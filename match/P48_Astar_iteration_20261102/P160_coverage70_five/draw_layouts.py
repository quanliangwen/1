"""New data plots from first-reviewed public RED exports; never true map/BLUE state."""
from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont

def draw_layouts(folder,rows,group_folder=None):
    F=Path(folder);G=Path(group_folder)if group_folder is not None else F/'P159_C70_ASTAR_A'
    assert json.loads((G/'CLIENT_FIRST_RAW_REVIEW.json').read_text())['status']=='PASS'
    font_path=Path('C:/Windows/Fonts/msyh.ttc')
    outputs={}
    for row in rows:
        name=row['map'];D=G/(name+'_red')
        image=Image.open(D/'round1_red_submitted.png').convert('L')
        if image.getextrema()[1]<=1:image=image.point(lambda p:p*255)
        W,H=image.size
        visual=json.loads((D/'round1_public_visual.json').read_text())
        assert visual['width']==W and visual['height']==H
        bombs=json.loads((D/'round1_bombs.json').read_text())['bombs']
        canvas=Image.new('RGB',(W,H+100),(18,22,32));canvas.paste(image.convert('RGB'),(0,80));draw=ImageDraw.Draw(canvas)
        font=ImageFont.truetype(str(font_path),max(13,min(20,W//55)))
        small=ImageFont.truetype(str(font_path),max(12,min(16,W//65)))
        draw.text((12,8),f"{name}  总分 {row['cluster_full']:.3f} / 原版 {row['baseline_full']:.3f}   投放 {row['placed']}/10",font=font,fill='white')
        draw.text((12,34),'底图：红队预测；彩线：红队公开轨迹；红圈：爆炸R；橙圈：选中的集中区2R',font=small,fill=(210,215,225))
        colors=[(60,200,255),(100,255,140),(240,130,255),(255,210,80),(100,170,255)]
        for i,track in enumerate(visual.get('tracks',[])):
            points=[(float(p[0]),float(p[1])+80)for p in track['points_pixel']]
            assert all(math.isfinite(x)and math.isfinite(y)for x,y in points)
            if len(points)>=2:draw.line(points,fill=colors[i%len(colors)],width=1)
        regions={}
        for a in row['concentration']:regions[(tuple(a['anchor']),a['radius'])]=a
        for(anchor,radius),a in regions.items():
            x,y=anchor[0]+W/2,H/2-anchor[1]+80
            draw.ellipse((x-radius,y-radius,x+radius,y+radius),outline=(255,160,0),width=3)
            draw.text((max(0,x-radius),max(82,y-radius)),f"集中 {a['actual_strict']} 枚",font=small,fill=(255,180,30))
        # Real official wall-score metadata supplies R, not an invented radius.
        r=json.loads((G/'RESULT.json').read_text())['jobs'][name]['rounds'][0]['phase']['wall_breakdown']['blast_radius']
        for i,bomb in enumerate(bombs):
            x,y=float(bomb['x'])+W/2,H/2-float(bomb['y'])+80
            draw.ellipse((x-r,y-r,x+r,y+r),outline=(180,65,65),width=1)
            draw.ellipse((x-5,y-5,x+5,y+5),fill=(255,70,70),outline='white',width=1)
            draw.text((x+7,y-10),str(i+1),font=small,fill=(255,100,90))
        label='无集中方案被接受'if row['actual_cluster_strict']is None else f"最大严格集中数量 {row['actual_cluster_strict']}（+12px容差为{row['actual_cluster_with12']}）"
        draw.text((12,H+82),label,font=small,fill=(220,220,225))
        target=F/(name+'_layout.png');canvas.save(target)
        assert Image.open(target).size==(W,H+100)
        outputs[target.name]=target.read_bytes()
    return outputs
