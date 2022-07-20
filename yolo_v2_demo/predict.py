import torch
import torch.nn as nn
from tqdm import tqdm
import os
from torch.utils.data import DataLoader
from Tool.V2 import *
from Tool.BaseTools import get_voc_data_loader
from V2.UTILS.get_pretrained_darknet_19 import get_pretained_dark_net_19
from V2.UTILS.model_define import YOLOV2Net, DarkNet19, DarkNet_19
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True


class Helper:
    def __init__(
            self,
            model: nn.Module,
            opt_data_set: YOLOV2DataSetConfig,
            opt_trainer: YOLOV2TrainerConfig,
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

        self.predictor = YOLOV2Predictor(
            self.opt_trainer.iou_th,
            self.opt_trainer.prob_th,
            self.opt_trainer.conf_th,
            self.opt_trainer.score_th,
            self.opt_data_set.pre_anchor_w_h,
            self.opt_data_set.kinds_name,
            self.opt_data_set.image_size,
            self.opt_data_set.grid_number
        )

        self.visualizer = YOLOV2Visualizer(
            model,
            self.predictor,
            self.opt_data_set.class_colors
        )

        self.evaluator = YOLOV2Evaluator(
            model,
            self.predictor
        )

    def go(
            self,
            data_loader_train: DataLoader,
            data_loader_test: DataLoader,
    ):

        # show predict
        saved_dir = 'temp/'
        os.makedirs(saved_dir, exist_ok=True)

        self.visualizer.show_detect_results(
            data_loader_test,
            saved_dir
        )
        # eval mAP
        self.evaluator.eval_detector_mAP(
            data_loader_train
        )

        # eval mAP
        self.evaluator.eval_detector_mAP(
            data_loader_test
        )



torch.cuda.set_device(1)
trainer_opt = YOLOV2TrainerConfig()
data_opt = YOLOV2DataSetConfig()

# dark_net_19 = get_pretained_dark_net_19(
#     '/home/dell/PycharmProjects/YOLO/pre_trained/darknet19_72.96.pth'
# )
dark_net_19 = DarkNet19()
net = YOLOV2Net(dark_net_19)

helper = Helper(
    net,
    data_opt,
    trainer_opt
)

voc_train_loader = get_voc_data_loader(
    data_opt.root_path,
    data_opt.year,
    data_opt.image_size,
    trainer_opt.batch_size,
    train=True
)
voc_test_loader = get_voc_data_loader(
    data_opt.root_path,
    data_opt.year,
    data_opt.image_size,
    trainer_opt.batch_size,
    train=False
)
helper.detector.load_state_dict(
    torch.load('/home/dell/data2/models/home/dell/PycharmProjects/YOLO/V2/model_pth_detector/550.pth')
)
helper.go(voc_train_loader, voc_test_loader)
