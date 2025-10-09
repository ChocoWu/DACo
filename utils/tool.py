import cv2
import json
import os


def visualize_vp_on_bev(bev_img_dir, output_dir, scan_id, vps, step):
    with open(os.path.join(bev_img_dir, 'allScans_Node2pix.json'), 'r') as f:
        node2pix = json.load(f)

    floor_to_vps = {}
    for i, vp in enumerate(vps):
        vp = vp[0]
        data = node2pix[scan_id][vp]
        floor_idx = data[2]
        if floor_idx not in floor_to_vps:
            floor_to_vps[floor_idx] = []
        if i == 0:
            label = "start"
        elif i == len(vps) - 1:
            label = f"now"
        else:
            label = str(i)
        floor_to_vps[floor_idx].append((vp, label))


    # 获取该 viewpoint 的信息
    for floor_idx, floor_vps in floor_to_vps.items():
        if 'XcA2TqTSSAj' in scan_id:
            floor_img_id = floor_idx        # this scan has some problems
        else:
            floor_img_id = floor_idx + 1   # 0-based → 1-based

        floor_img_name = f"floor{floor_img_id}.png"
        floor_img_path = os.path.join(bev_img_dir, scan_id, floor_img_name)
        
        img = cv2.imread(floor_img_path)

        # draw all the viewpoints of this floor
        for i, (vp, label) in enumerate(floor_vps):
            data = node2pix[scan_id][vp]
            x, y = data[0]  # [x, y]
            center = (int(x), int(y))
            radius = 10
            thickness = 3

            if label == 'start':
                color = (0, 0, 255)
            elif label == 'now':
                color = (0, 255, 0)
            else:
                color = (255, 0, 0)
            cv2.circle(img, center, radius, color, thickness)
            cv2.putText(img, label, (int(x) + 10, int(y) - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        os.makedirs(output_dir, exist_ok=True)
        if step == None:
            cv2.imwrite(os.path.join(output_dir, f"floor{floor_img_id}_traj.png"), img)
        else:
            cv2.imwrite(os.path.join(output_dir, f"floor{floor_img_id}_step{step}.png"), img)

    