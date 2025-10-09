DATA_ROOT=datasets
EXP_NAME=test
outdir=test_results/${EXP_NAME}
SPLIT_TYPE=mapgpt72       # mapgpt72, r2r, reverie
DATASET_TYPE=r2r        # r2r, reverie

# split option: R2R_val_unseen_enc, MapGPT_72_scenes_processed, REVERIE_processed_200

flag="--root_dir ${DATA_ROOT}
      --img_root data/Matterport3D/v1/RGB_Observations/
      --bev_dir data/Matterport3D/v1/bev_images
      --traj_img_dir bev_with_traj/${SPLIT_TYPE}
      --split MapGPT_72_scenes_processed
      --output_dir ${outdir}
      --dataset ${DATASET_TYPE}
      --max_action_len 15
      --max_re_plan 1
      --llm model/Qwen2_5_VL_32B_Instruct
      --max_tokens 1000
      "

python main.py $flag 