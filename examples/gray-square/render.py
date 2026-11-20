"""Build original cards and a silent review cut with Pillow, FFmpeg and Noto Sans CJK KR."""
import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
TIMELINE = [
    (5, '두 칸 중 어느 쪽이 더 밝아 보이나요?', '회색 칸을 비교해 보세요'),
    (5, '가운데 칸만 남겨 볼게요.', '배경을 걷어 보면'),
    (6, '두 칸 모두 RGB 값이 136, 136, 136입니다.', '가운데 픽셀 값'),
    (6, '같은 회색을 다른 바탕 위에 놓았습니다.', '달라진 것은 바탕색'),
]
INK = '#151E2D'
PAPER = '#F6F3EC'
GRAY = (136, 136, 136)


def render(fontfile, outdir):
    outdir.mkdir(parents=True, exist_ok=True)

    def font(size):
        return ImageFont.truetype(fontfile, size)

    def card(index, thumbnail=False):
        image = Image.new('RGB', (1280, 720), PAPER)
        draw = ImageDraw.Draw(image)
        title = '어느 쪽이 더 밝을까?' if thumbnail else TIMELINE[index][2]
        draw.text((640, 106), title, font=font(64), anchor='mm', fill=INK)
        for center, background in [(382, '#232323'), (898, '#E8E8E8')]:
            if index in (0, 3):
                draw.rectangle((center-237, 200, center+237, 505), fill=background)
            draw.rectangle((center-75, 280, center+75, 430), fill=GRAY)
            if index == 2:
                draw.text((center, 475), '#888888', font=font(34), fill=INK, anchor='mm')
            assert image.getpixel((center, 355)) == GRAY
        if not thumbnail:
            draw.rounded_rectangle((96, 570, 1184, 683), radius=16, fill=INK)
            draw.text((640, 623), TIMELINE[index][1], anchor='mm', font=font(40), fill='white')
        return image

    card(0, True).save(outdir / 'thumbnail.png')
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        commands = []
        for i, (duration, _, _) in enumerate(TIMELINE):
            card(i).save(work / f'{i}.png')
            commands.extend([f"file '{i}.png'", f'duration {duration}'])
        commands.append(f"file '{len(TIMELINE)-1}.png'")
        (work / 'scenes.txt').write_text('\n'.join(commands) + '\n')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat',
                        '-i', str(work / 'scenes.txt'), '-vf', 'fps=25,format=yuv420p', '-t',
                        str(sum(row[0] for row in TIMELINE)), '-c:v', 'libx264', '-crf', '20',
                        '-movflags', '+faststart', str(outdir / 'review.mp4')], check=True)
    elapsed = 0
    cues = []
    for number, (duration, line, _) in enumerate(TIMELINE, 1):
        cues.append(f'{number}\n00:00:{elapsed:02},000 --> 00:00:{elapsed+duration:02},000\n{line}\n')
        elapsed += duration
    (outdir / 'captions.srt').write_text('\n'.join(cues), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--font', default='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
    parser.add_argument('--out', type=Path, default=ROOT)
    args = parser.parse_args()
    render(args.font, args.out)
