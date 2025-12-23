from flask import Flask, render_template, request, jsonify
import os
import sys
from pathlib import Path
import traceback

# Add parent directory to path to import core logic
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fast_video_slice import (
    TimeRange, parse_hms, check_files, read_srt, ensure_outdir,
    ensure_ffmpeg_exists, run_ffmpeg, slice_cues, write_srt,
    sanitize_title, UserError
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-fast-video-slice'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(__file__), 'outputs')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'video' not in request.files or 'srt' not in request.files:
        return jsonify({'status': 'error', 'message': '缺少影片或字幕檔案'}), 400
    
    video = request.files['video']
    srt = request.files['srt']
    
    if video.filename == '' or srt.filename == '':
        return jsonify({'status': 'error', 'message': '未選擇檔案'}), 400

    video_path = os.path.join(app.config['UPLOAD_FOLDER'], video.filename)
    srt_path = os.path.join(app.config['UPLOAD_FOLDER'], srt.filename)
    
    video.save(video_path)
    srt.save(srt_path)
    
    return jsonify({
        'status': 'success', 
        'message': '檔案上傳成功',
        'video_filename': video.filename,
        'srt_filename': srt.filename
    })

@app.route('/slice', methods=['POST'])
def slice_video():
    data = request.json
    video_filename = data.get('video_filename')
    srt_filename = data.get('srt_filename')
    ranges_data = data.get('ranges')

    if not video_filename or not srt_filename or not ranges_data:
        return jsonify({'status': 'error', 'message': '缺少必要參數'}), 400

    video_path = Path(app.config['UPLOAD_FOLDER']) / video_filename
    srt_path = Path(app.config['UPLOAD_FOLDER']) / srt_filename
    outdir = Path(app.config['OUTPUT_FOLDER'])

    try:
        # 1. Check files
        check_files(video_path, srt_path)
        
        # 2. Parse ranges
        parsed_ranges = []
        for r in ranges_data:
            start_str = r.get('start')
            end_str = r.get('end')
            title = r.get('title')
            
            try:
                start = parse_hms(start_str)
                end = parse_hms(end_str)
            except UserError as e:
                return jsonify({'status': 'error', 'message': f"時間格式錯誤: {e}"}), 400
                
            if start >= end:
                return jsonify({'status': 'error', 'message': f"區間無效: {start_str} -> {end_str} (開始時間需小於結束時間)"}), 400
            
            safe_title = sanitize_title(title) if title else None
            label = f"{start_str} -> {end_str}"
            parsed_ranges.append(TimeRange(start=start, end=end, label=label, title=title, safe_title=safe_title))

        # 3. Prepare environment
        ensure_outdir(outdir)
        ffmpeg_cmd, _ = ensure_ffmpeg_exists()
        cues = read_srt(srt_path)
        
        generated_files = []

        # 4. Process ranges
        for idx, rng in enumerate(parsed_ranges, start=1):
            base = rng.safe_title if rng.safe_title else f"clip_{idx:03d}"
            # Ensure unique filename to avoid overwriting if multiple users or repeated runs (simple timestamp or uuid could be better for prod)
            # For now, we just use the base name but handle potential conflicts if needed, 
            # though the logic below overwrites if exists in output folder or fails based on run_ffmpeg check.
            # fast_video_slice.py's run_ffmpeg raises error if exists. Let's remove if exists for web version convenience.
            
            video_out = outdir / f"{base}.mp4"
            subs_out = outdir / f"{base}.srt"
            
            if video_out.exists():
                os.remove(video_out)
            if subs_out.exists():
                os.remove(subs_out)

            run_ffmpeg(video_path, rng, video_out, False, ffmpeg_cmd)
            sliced_cues = slice_cues(cues, rng)
            write_srt(subs_out, sliced_cues)
            
            generated_files.append(video_out.name)
            generated_files.append(subs_out.name)

        return jsonify({
            'status': 'success', 
            'message': '裁切完成', 
            'files': generated_files,
            'output_dir': str(outdir)
        })

    except UserError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f"系統錯誤: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
