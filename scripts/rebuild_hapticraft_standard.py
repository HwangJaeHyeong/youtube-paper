"""Existing PaperCast shorts layout, literal English/numerals, word-aligned Puck.

Requires the saved continuous take and transcription in this slug's audio folder.
Uses the project's unmodified header/footer renderer and shorts composer.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageOps
from pydub import AudioSegment

from src.video import word_timing as sync
from src.config import AUDIO_DIR, SCRIPTS_DIR, VIDEOS_DIR
from src.video import composer, title_card

SLUG = "hapticraft-standard-shorts"
ROOT = AUDIO_DIR / SLUG


def canonical(text):
    text = re.sub(r"[^가-힣a-zA-Z0-9]", "", text).lower()
    for a, b in [
        ("열여덟", "18"), ("십팔", "18"), ("일곱", "7"), ("이천이십육", "2026"),
        ("햅틱크래프트", "hapticraft"), ("햅티크래프트", "hapticraft"),
        ("하티크래프트", "hapticraft"),
        ("포스텍", "postech"), ("코리아테크", "koreatech"), ("코리아텍", "koreatech"),
        ("한국기술교육대", "koreatech"), ("아이이이이", "ieee"), ("아이트리플이", "ieee"),
        ("티브이씨지", "tvcg"), ("티브이시지", "tvcg"), ("티비씨지", "tvcg"),
    ]:
        text = text.replace(a,b)
    return text


def panel(key, manifest):
    info = manifest["panels"][key]
    image = Image.open(info["path"]).convert("RGB")
    # Original figure panels, including their original annotations. Never paint
    # over source pixels or add editorial labels to a figure.
    component = {"shape": (0,0,1/3,.5), "vibration": (1/3,0,2/3,.5), "impact": (2/3,0,1,.5), "thermal": (0,.5,1/3,1), "stiffness": (2/3,.5,1,1)}
    if key in component:
        source=Image.open(AUDIO_DIR/"hapticraft-paper-shorts"/"originals"/"fig3.jpeg").convert("RGB")
        rect=tuple(round(v*(source.width if i%2==0 else source.height)) for i,v in enumerate(component[key]))
        image=source.crop(rect)
    return image


def main():
    data = json.loads((SCRIPTS_DIR/f"{SLUG}.json").read_text())
    response = json.loads((ROOT/"transcription-response.json").read_text())
    recognized = list(sync.words_from_response(response))
    sync.normalized = canonical
    tokens, similarity = sync.align_words(data,recognized)
    (ROOT/"aligned-words.json").write_text(json.dumps({"similarity":similarity,"words":tokens},ensure_ascii=False,indent=2)+"\n")
    audio=ROOT/"narration-1.2x.wav"
    duration=len(AudioSegment.from_wav(audio))/1000
    ass=ROOT/f"{SLUG}.ass"
    sync.build_subtitles(tokens,ass)
    # Restore the actual existing hype style, while retaining ASR word timings.
    text=ass.read_text().replace("Pretendard Black,78,","Pretendard Black,88,")
    # Same hype typography, below the actual art so parts and graph bars stay visible.
    text=text.replace(r"\pos(540,1380)",r"\pos(540,1320)")
    text=text.replace(r"\fad(20,0)\fscx95\fscy95\t(0,60,\fscx100\fscy100)",r"\fad(30,0)\fscx80\fscy80\t(0,110,\fscx100\fscy100)")
    ass.write_text(text)
    manifest=json.loads((AUDIO_DIR/"hapticraft-paper-shorts"/"crop-manifest.json").read_text())
    shots=json.loads((AUDIO_DIR/"hapticraft-puck-sync-shorts"/"sync-manifest.json").read_text())["shots"]
    expanded=[]
    for shot in shots:
        if shot["keys"]==["vibration","impact"]:
            first=dict(shot);first["keys"]=["vibration"]
            second=dict(shot);second["keys"]=["impact"];second["cue"]="탁"
            expanded.extend([first,second])
        else:
            expanded.append(shot)
    shots=expanded
    crops=ROOT/"crops";crops.mkdir(exist_ok=True)
    segments=[]
    for i,shot in enumerate(shots):
        candidates=[t for t in tokens if t["line"]==shot["line"]]
        if shot["cue"]!="line start":
            candidates=[t for t in candidates if canonical(t["text"]).startswith(canonical(shot["cue"]))]
        assert candidates,shot
        shot["start"]=max(0,candidates[0]["start"]-0.04) if i else 0
        images=[panel(k,manifest) for k in shot["keys"]]
        if len(images)==1:
            art=images[0]
        elif shot["keys"]==["gun","cup"]:
            # Keep each VR/physical pair together, stacked rather than four tiny
            # images side by side.
            scaled=[]
            for im in images:
                scaled.append(im.resize((1000,round(im.height*1000/im.width)),Image.Resampling.LANCZOS))
            art=Image.new("RGB",(1000,sum(im.height for im in scaled)+20),"white")
            y=0
            for im in scaled:
                art.paste(im,(0,y));y+=im.height+20
        else:
            # A plain crop collage; no replacement slide titles, badges or cards.
            target_h=800
            scaled=[ImageOps.contain(im,(1000,target_h),Image.Resampling.LANCZOS) for im in images]
            art=Image.new("RGB",(sum(im.width for im in scaled)+24*(len(scaled)-1),target_h),"white")
            x=0
            for im in scaled:
                art.paste(im,(x,(target_h-im.height)//2));x+=im.width+24
        if "all_results" in shot["keys"]:
            # Reuse the actual original legend pixels, without redrawing text.
            original=Image.open(AUDIO_DIR/"hapticraft-paper-shorts"/"originals"/"fig16.jpeg").convert("RGB")
            legend=original.crop((round(.238*original.width),round(.959*original.height),round(.795*original.width),original.height))
            legend=legend.resize((art.width,round(legend.height*art.width/legend.width)),Image.Resampling.LANCZOS)
            canvas=Image.new("RGB",(art.width,art.height+legend.height+10),"white");canvas.paste(art,(0,0))
            canvas.paste(legend,(0,art.height+10))
            art=canvas
        # The composer scales this canvas to 88% during its standard entrance.
        # The resulting art stays within x=65..1015, y=555..1215; header, speech
        # caption (y=1320) and footer (y=1450+) each retain separate space.
        canvas=Image.new("RGB",(1080,1920),(20,22,30))
        fitted=ImageOps.contain(art,(1080,750),Image.Resampling.LANCZOS)
        art_box=((1080-fitted.width)//2,500+(750-fitted.height)//2)
        canvas.paste(fitted,art_box)
        shot["source_art_size"]=list(art.size)
        shot["placed_art_size"]=list(fitted.size)
        shot["canvas_art_box"]=[*art_box,art_box[0]+fitted.width,art_box[1]+fitted.height]
        path=crops/f"shot_{i:02d}.png";canvas.save(path);shot["crop"]=str(path)
    for i,shot in enumerate(shots):
        end=shots[i+1]["start"] if i+1<len(shots) else duration
        start_frame=round(shot["start"]*30);end_frame=round(end*30)
        assert end_frame>start_frame
        shot.update(start_frame=start_frame,end_frame=end_frame,end=end)
        segments.append((Path(shot["crop"]),(end_frame-start_frame)/30))
    header=crops/"__HEADER__.png";footer=crops/"__FOOTER__.png"
    title_card.render_header_strip(data["title_hook"],header,width=1080)
    title_card.render_footer_strip("다음 논문은 **댓글**로 추천 받아요",footer,width=1080)
    data["metadata"].update(estimated_duration_sec=round(duration),playback_speed=1.2,voice="Puck",continuous_take=True)
    data["metadata"]["notation"]="Original English spellings and Arabic numerals retained in TTS input and subtitles."
    (SCRIPTS_DIR/f"{SLUG}.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    (ROOT/"sync-manifest.json").write_text(json.dumps({"duration":duration,"similarity":similarity,"shots":shots},ensure_ascii=False,indent=2)+"\n")
    data["metadata"]["figure_policy"]="Only original PDF figure pixels; no added figure labels, masks, or redrawn legends."
    (SCRIPTS_DIR/f"{SLUG}.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    out=VIDEOS_DIR/f"{SLUG}-figures-only-1.2x.mp4"
    print(f"Rendering existing shorts format: {len(segments)} shots, {duration:.3f}s, similarity={similarity:.3f}",flush=True)
    font_dir=Path(__file__).resolve().parent.parent/"assets"/"fonts"
    composer.compose_shorts(audio,ass,[],segments,out,header_png=header,footer_png=footer,font_dir=font_dir)
    print("DONE",out,flush=True)


if __name__=="__main__":
    main()
