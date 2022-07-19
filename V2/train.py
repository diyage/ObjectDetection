import torch
import torch.nn as nn
from tqdm import tqdm
import os
from torch.utils.data import DataLoader
from Tool.V2 import YOLOV2Trainer, Predictor, Visualizer, Evaluator, YOLOV2Loss, DataSetConfig, TrainConfig
from Tool.BaseTools import get_voc_data_loader
from V2.UTILS.get_pretrained_darknet_19 import get_pretained_dark_net_19
from V2.UTILS.model_define import YOLOV2Net, DarkNet19
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True


class Helper:
    def __init__(
            self,
            model: nn.Module,
            opt_data_set: DataSetConfig,
            opt_trainer: TrainConfig,
    ):
        self.detector = model  # type: nn.Module
        self.detector.cuda()

        self.dark_net = model.darknet19  # type: nn.Module
        self.dark_net.cuda()
        # be careful, darknet19 is not the detector

        self.opt_data_set = opt_data_set
        self.opt_trainer = opt_trainer

        self.trainer = YOLOV2Trainer(
            model,
            self.opt_data_set.pre_anchor_w_h,
            self.opt_data_set.image_size,
            self.opt_data_set.grid_number,
            self.opt_data_set.kinds_name
        )

        self.predictor = Predictor(
            self.opt_trainer.iou_th,
            self.opt_trainer.prob_th,
            self.opt_trainer.conf_th,
            self.opt_trainer.score_th,
            self.opt_data_set.pre_anchor_w_h,
            self.opt_data_set.kinds_name,
            self.opt_data_set.image_size,
            self.opt_data_set.grid_number
        )

        self.visualizer = Visualizer(
            model,
            self.predictor,
            self.opt_data_set.class_colors
        )

        self.evaluator = Evaluator(
            model,
            self.predictor
        )

    def go(
            self,
            data_loader_train: DataLoader,
            data_loader_test: DataLoader,
    ):
        loss_func = YOLOV2Loss(
            self.opt_data_set.pre_anchor_w_h,
            self.opt_trainer.weight_position,
            self.opt_trainer.weight_conf_has_obj,
            self.opt_trainer.weight_conf_no_obj,
            self.opt_trainer.weight_cls_prob,
            self.opt_data_set.grid_number,
            self.opt_data_set.image_size,
            iou_th=self.opt_trainer.iou_th,
        )
        # already trained dark_net 19
        # so just train detector
        # optimizer = torch.optim.Adam(self.detector.parameters(), lr=self.opt_trainer.lr)
        optimizer = torch.optim.SGD(
            self.detector.parameters(),
            lr=self.opt_trainer.lr,
            momentum=0.9,
            weight_decay=5e-4
        )

        for epoch in tqdm(range(self.opt_trainer.max_epoch_on_detector),
                          desc='training detector',
                          position=0):

            loss_dict = self.trainer.train_detector_one_epoch(
                data_loader_train,
                loss_func,
                optimizer,
                desc='train for detector epoch --> {}'.format(epoch)
            )

            print_info = 'loss info--> '
            for key, val in loss_dict.items():
                print_info += ' {}:{:.5f}. '.format(key, val)
            print(print_info)

            if epoch % 10 == 0:
                # save model
                saved_dir = self.opt_trainer.ABS_PATH + os.getcwd() + '/model_pth_detector/'
                os.makedirs(saved_dir, exist_ok=True)
                torch.save(self.detector.state_dict(), '{}/{}.pth'.format(saved_dir, epoch))

                # show predict
                saved_dir = self.opt_trainer.ABS_PATH + os.getcwd() + '/eval_images/{}/'.format(epoch)
                os.makedirs(saved_dir, exist_ok=True)

                self.visualizer.show_detect_results(
                    data_loader_test,
                    saved_dir
                )

                # eval mAP
                self.evaluator.eval_detector_mAP(
                    data_loader_test
                )


torch.cuda.set_device(1)
trainer_opt = TrainConfig()
data_opt = DataSetConfig()

# dark_net = get_pretained_dark_net_19('/home/dell/PycharmProjects/YOLO/pre_trained/darknet19_72.96.pth')
dark_net_19 = DarkNet19()
net = YOLOV2Net(dark_net_19)

helper = Helper(
    net,
    data_opt,
    trainer_opt
)

voc_train_loader = get_voc_data_loader(
    data_opt.root_path,
    data_opt.image_size,
    trainer_opt.batch_size,
    train=True
)
voc_test_loader = get_voc_data_loader(
    data_opt.root_path,
    data_opt.image_size,
    trainer_opt.batch_size,
    train=False
)
helper.go(voc_train_loader, voc_test_loader)

