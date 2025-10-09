import os
import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument('--data_dir', type=str, default='datasets')
    parser.add_argument('--dataset', type=str, default='r2r')
    parser.add_argument('--output_dir', type=str, default='default', help='experiment id')
    parser.add_argument('--seed', type=int, default=2025)
    parser.add_argument('--img_root', type=str, default=None)
    parser.add_argument('--bev_dir', type=str, default=None)
    parser.add_argument('--traj_img_dir', type=str, default=None)
    parser.add_argument('--num_workers', type=int, default=4, help='for parallel evaluation')

    # Data preparation
    parser.add_argument('--max_instr_len', type=int, default=200)
    parser.add_argument('--max_action_len', type=int, default=15, help='max attempts of 2D-LLM')
    parser.add_argument('--max_re_plan', type=int, default=1, help='max request count of re-plan to 3D-LLM')
    parser.add_argument('--max_retries_llm', type=int, default=2, help='max retry count of LLM, preventing llm doesn\'t output a valid format')
    parser.add_argument('--batch_size', type=int, default=1)  # only support bach_size=1
    parser.add_argument("--split", type=str, default='MapGPT_72_scenes_processed')
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--end', type=int, default=None)

    # LLM
    parser.add_argument('--llm', type=str, default='', help='path to llm')
    parser.add_argument('--max_tokens', type=int, default=1000)

    args, _ = parser.parse_known_args()

    args = postprocess_args(args)
    
    return args


def postprocess_args(args):
    DATA_DIR = args.data_dir

    args.connectivity_dir = os.path.join(DATA_DIR, 'R2R', 'connectivity')
    args.scan_data_dir = os.path.join(DATA_DIR, 'Matterport3D', 'v1_unzip_scans')

    if args.dataset == 'r2r':
        args.anno_dir = os.path.join(DATA_DIR, 'R2R', 'annotations')
    elif args.dataset == 'reverie':
        args.anno_dir = os.path.join(DATA_DIR, 'REVERIE', 'annotations')


    # Build paths
    args.log_dir = os.path.join(args.output_dir, 'logs')
    args.pred_dir = os.path.join(args.output_dir, 'preds')

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs(args.pred_dir, exist_ok=True)

    return args
