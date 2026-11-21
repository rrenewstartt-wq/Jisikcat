"""Render the episode from the approved-for-edit voice take, cue sheet and hourly prices."""
import csv
import json
import math
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EP = Path(__file__).resolve().parents[1]
CUES = list(csv.reader((EP / 'script/cues.tsv').open(), delimiter='\t'))
PRICES = [float(r['EUR_per_MWh']) for r in csv.DictReader((EP/'assets/prices.csv').open())]
TIMES = json.loads((EP/'edit/timings.json').read_text())
INK, PAPER, LIME, TEAL, DIM = '#122C31', '#F5F1DF', '#DCFA67', '#00756D', '#53716F'
WHITE = '#FFFFFF'
FPS = 24


@lru_cache(None)
def font(size, bold=True):
    name = 'Bold' if bold else 'Regular'
    return ImageFont.truetype(f'/usr/share/fonts/opentype/noto/NotoSansCJK-{name}.ttc',size,index=1)


def label(draw, xy, text, size, color=INK, bold=True, anchor='la'):
    draw.text(xy,text,font=font(size,bold),fill=color,anchor=anchor)


def ticket(draw, x, y, w, h, title, value, unit, dark=False):
    color = INK if dark else PAPER
    fg = PAPER if dark else INK
    draw.rounded_rectangle((x,y,x+w,y+h),12,fill=color,outline=fg,width=2)
    for xx in range(x+16,x+w-8,16):
        draw.line((xx,y+76,xx+7,y+76),fill=DIM,width=2)
    label(draw,(x+25,y+18),title,31,fg)
    label(draw,(x+25,y+96),value,67,LIME if dark else TEAL)
    label(draw,(x+28,y+h-50),unit,23,fg,False)


def washer(draw, x, y, size):
    w=size
    draw.rounded_rectangle((x,y,x+w,y+w),radius=22,fill=PAPER,outline=INK,width=6)
    draw.line((x+3,y+w*.23,x+w-3,y+w*.23),fill=INK,width=5)
    draw.rounded_rectangle((x+w*.09,y+w*.08,x+w*.35,y+w*.15),4,fill=TEAL)
    for frac in (.72,.85):
        cx=x+w*frac; cy=y+w*.12; draw.ellipse((cx-6,cy-6,cx+6,cy+6),fill=INK)
    cx,cy,r=x+w*.5,y+w*.60,w*.305
    draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill=TEAL,outline=INK,width=6)
    draw.chord((cx-r*.80,cy-r*.80,cx+r*.80,cy+r*.80),10,166,fill=LIME)
    draw.arc((cx-r*.72,cy-r*.72,cx+r*.72,cy+r*.72),195,268,fill=PAPER,width=6)


def chart(draw, index):
    x0,x1,yzero=116,1128,338
    x=lambda h: x0+(x1-x0)*h/23
    y=lambda value: yzero-value*1.30
    for v in (75,0,-75,-150):
        yy=y(v);draw.line((x0,yy,x1,yy),fill=TEAL if v==0 else '#B8C6BA',width=3 if v==0 else 1)
        label(draw,(x0-12,yy),str(v),17,DIM,False,'rm')
    points=[(x(h),y(v)) for h,v in enumerate(PRICES)]
    steps=[points[0]]
    for xx,yy in points[1:]:
        steps.extend([(xx,steps[-1][1]),(xx,yy)])
    draw.line(steps,fill=TEAL,width=4,joint='curve')
    h=[0,8,9,13,18][index-3]
    tx,ty=points[h];draw.line((tx,ty,tx,553),fill=DIM,width=1)
    draw.ellipse((tx-10,ty-10,tx+10,ty+10),fill=LIME,outline=INK,width=3)
    for tick in (0,6,12,18,23):label(draw,(x(tick),560),f'{tick:02d}시',19,DIM,False,'mm')
    label(draw,(1127,186),f'{h:02d}시    {PRICES[h]:+.2f} €/MWh',29,TEAL,True,'ra')


def arrow(draw, y, reverse, color, tag):
    a,b=(810,475) if reverse else (475,810)
    sign=1 if b>a else -1
    draw.line((a,y,b,y),fill=color,width=9)
    draw.polygon([(b,y),(b-22*sign,y-14),(b-22*sign,y+14)],fill=color)
    label(draw,(640,y-43),tag,23,color,True,'ma')


def scene(i):
    kind=CUES[i][0]; dark=kind in ('flow','units','plant')
    bg,fg=(INK,PAPER) if dark else (PAPER,INK)
    image=Image.new('RGB',(1280,720),bg); d=ImageDraw.Draw(image)
    info={
        'receipt':('전력시장 관찰 기록','전기 가격에 찍힌 마이너스'),
        'chart':('Bundesnetzagentur · SMARD  /  2024.05.12  /  현지 시각','도매가격이 0을 통과한 날'),
        'flow':('하루 전 거래  /  정산 방향','누가 누구에게 돈을 냈을까?'),
        'units':('단위 환산','같은 가격, 다른 단위'),
        'plant':('발전소의 선택  /  설명용 상황','멈추는 데도 비용이 든다면'),
        'bill':('소매 계약','가정의 영수증을 펼쳐 보면'),
        'math':('가상 계약  /  1 kWh 추가 사용','부호를 바꾸는 건 추가 단가'),
        'end':('같은 한 시간  /  두 장의 영수증','세탁기를 돌린 집의 답은?')}
    meta,title=info[kind];label(d,(78,35),meta,23,LIME if dark else TEAL)
    d.line((78,80,1202,80),fill=DIM,width=2);label(d,(73,93),title,55,fg)
    if kind in ('receipt','end'):
        ticket(d,120,230,544,288,'도매 거래  /  13시','−135.45','유로 / MWh  ·  독일–룩셈부르크',True)
        washer(d,810,216,270);label(d,(945,505),'우리 집 청구액은?',29,TEAL,True,'ma')
    elif kind=='chart':chart(d,i)
    elif kind=='flow':
        for cx,name in ((260,'판매자'),(1020,'구매자')):
            d.rounded_rectangle((cx-135,280,cx+135,440),22,fill=PAPER);label(d,(cx,357),name,45,INK,True,'mm')
        arrow(d,315,False,PAPER,'약정한 전력');arrow(d,441,False,LIME,'음수 가격의 정산금')
    elif kind=='units':
        label(d,(95,242),'1 MWh',74,PAPER);label(d,(598,242),'1,000 kWh',74,LIME)
        label(d,(490,265),'=',52,PAPER);d.line((95,374,1150,374),fill=DIM,width=2)
        label(d,(99,422),'−135.45 €/MWh',42,PAPER);label(d,(598,417),'−13.545 ct/kWh',48,LIME)
    elif kind=='plant':
        for x,n,label1,sub in ((85,'A','계속 공급','음수 가격으로 한 시간 거래'),(659,'B','가동 중단','정지 비용 + 재가동 비용')):
            d.rounded_rectangle((x,235,x+530,483),15,outline=DIM,width=3)
            label(d,(x+28,254),n,28,LIME);label(d,(x+28,310),label1,54,PAPER);label(d,(x+30,415),sub,26,PAPER,False)
    elif kind=='bill':
        ticket(d,85,233,531,284,'고정 단가 계약','약정 단가','요금표에 정해진 단가 적용')
        ticket(d,648,233,546,284,'시장 연동 계약','시간별 단가','시장가격 + 적용되는 요금 항목',True)
    elif kind=='math':
        low=i>=25
        ticket(d,85,226,538,296,'도매 성분','−13.545','유로센트 / kWh')
        ticket(d,651,226,549,296,'추가 단가 '+('8센트' if low else '18센트'),('≈ −5.55' if low else '≈ +4.46'),'합계  ·  유로센트 / kWh',True)
    return image


def timestamp(seconds):
    ms=round(seconds*1000);return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'


def wrap(text, pixels):
    lines=[];line=''
    for word in text.split():
        merged=(line+' '+word).strip()
        if line and font(34).getlength(merged)>pixels:lines.append(line);line=word
        else:line=merged
    return '\n'.join(lines+[line])


def thumbnail():
    im=Image.new('RGB',(1280,720),LIME);d=ImageDraw.Draw(im)
    d.rounded_rectangle((-138,455,680,920),120,fill='#BED947');d.line((70,106,745,106),fill=INK,width=3)
    label(d,(73,51),'독일 전력시장   /   실제 가격표',31,INK)
    label(d,(62,151),'전기값이',108);label(d,(60,288),'마이너스?',124)
    washer(d,846,166,338)
    d.rounded_rectangle((76,538,724,623),14,fill=INK);label(d,(103,544),'−135.45 유로 / MWh',48,LIME)
    im.save(EP/'thumbnail/thumbnail.jpg',quality=93)


def main():
    thumbnail(); subs=[];frames=[round(start*FPS) for start,_ in TIMES]+[math.ceil(TIMES[-1][1]*FPS)]
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp); concat=[]
        for i,((start,stop),row) in enumerate(zip(TIMES,CUES)):
            text=wrap(row[1],950);subs.append(f'{i+1}\n{timestamp(start)} --> {timestamp(stop)}\n{text}\n'); n=frames[i+1]-frames[i]
            im=scene(i); im.save(tmp/'frame.png'); xs=tmp/f'clip{i:02}.mp4'; concat.append("file '"+xs.name+"'")
            motion=f"zoompan=z='1+0.014*on/{max(1,n-1)}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={n}:s=1280x720:fps={FPS}"
            subprocess.run(['ffmpeg','-loglevel','error','-y','-i',str(tmp/'frame.png'),'-vf',motion,'-frames:v',str(n),'-pix_fmt','yuv420p','-c:v','libx264','-threads','2','-preset','veryfast','-crf','19',str(xs)],check=True)
        srt=EP/'edit/captions.srt';srt.write_text('\n'.join(subs),encoding='utf-8'); (tmp/'clips.txt').write_text('\n'.join(concat))
        style="FontName=Noto Sans CJK KR,FontSize=20,Bold=1,Outline=1,Shadow=0,BorderStyle=3,OutlineColour=&H00272C1E,MarginV=15"
        subprocess.run(['ffmpeg','-loglevel','error','-y','-f','concat','-safe','0','-i',str(tmp/'clips.txt'),'-i',str(EP/'audio/narration.wav'),'-vf',f"subtitles=edit/captions.srt:force_style='{style}'",'-af','loudnorm=I=-16:TP=-1.5:LRA=9','-c:a','aac','-ar','48000','-b:a','144k','-c:v','libx264','-threads','3','-preset','veryfast','-crf','19','-movflags','+faststart',str(EP/'edit/master.mp4')],cwd=EP,check=True)


if __name__=='__main__':main()
