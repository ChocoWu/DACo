DATA_ROOT=datasets
EXP_NAME=test
OUTDIR=test_results/${EXP_NAME}
DATASET_TYPE=r4r        # r2r, reverie, r4r
# export BASE_URL="http://127.0.0.1:8000/v1"
# split option: R2R_val_unseen_enc, MapGPT_72_scenes_processed, REVERIE_processed_200, R4R_processed_200
SPLIT=R4R_processed_200
MODEL=CUSTOMIZE_YOUR_MODEL

flag="--root_dir ${DATA_ROOT}
      --img_root /scratch/e1553754/data/Matterport3D/v1/RGB_Observations/
      --bev_dir /scratch/e1553754/data/Matterport3D/v1/bev_images
      --traj_img_dir bev_with_traj/${EXP_NAME}/
      --split ${SPLIT}
      --output_dir ${OUTDIR}
      --dataset ${DATASET_TYPE}
      --max_action_len 30
      --max_re_plan 1
      --llm ${MODEL}
      --max_tokens 1000
      --global_style dynamic
      "

python main.py $flag 