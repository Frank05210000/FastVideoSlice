document.addEventListener('DOMContentLoaded', function() {
    const addRangeBtn = document.getElementById('addRangeBtn');
    const rangesContainer = document.getElementById('rangesContainer');
    const startSliceBtn = document.getElementById('startSliceBtn');
    const resultsArea = document.getElementById('resultsArea');
    const progressBar = document.querySelector('.progress-bar');
    const logOutput = document.getElementById('logOutput');

    // Add new range
    addRangeBtn.addEventListener('click', function() {
        const rangeItem = document.querySelector('.range-item').cloneNode(true);
        // Clear inputs
        rangeItem.querySelectorAll('input').forEach(input => input.value = '');
        // Add remove event
        setupRemoveBtn(rangeItem.querySelector('.remove-range-btn'));
        rangesContainer.appendChild(rangeItem);
    });

    // Setup initial remove button
    setupRemoveBtn(document.querySelector('.remove-range-btn'));

    function setupRemoveBtn(btn) {
        btn.addEventListener('click', function() {
            if (document.querySelectorAll('.range-item').length > 1) {
                this.closest('.range-item').remove();
            } else {
                alert('至少需要保留一個區間');
            }
        });
    }

    // Mock Start Process
    startSliceBtn.addEventListener('click', async function() {
        // Basic validation
        const videoFile = document.getElementById('videoFile').files[0];
        const srtFile = document.getElementById('srtFile').files[0];
        
        if (!videoFile || !srtFile) {
            alert('請選擇影片與字幕檔案');
            return;
        }

        // Show results area
        resultsArea.classList.remove('d-none');
        startSliceBtn.disabled = true;
        startSliceBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 處理中...';
        logOutput.innerHTML = '';
        progressBar.style.width = '0%';

        try {
            // 1. Upload Files
            logOutput.innerHTML += '<div>[INFO] 開始上傳檔案...</div>';
            const formData = new FormData();
            formData.append('video', videoFile);
            formData.append('srt', srtFile);

            const uploadRes = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!uploadRes.ok) throw new Error('上傳失敗');
            const uploadData = await uploadRes.json();
            logOutput.innerHTML += '<div>[INFO] 檔案上傳完成</div>';
            progressBar.style.width = '30%';

            // 2. Collect Ranges
            const ranges = [];
            document.querySelectorAll('.range-item').forEach(item => {
                const inputs = item.querySelectorAll('input');
                ranges.push({
                    start: inputs[0].value,
                    end: inputs[1].value,
                    title: inputs[2].value
                });
            });

            // 3. Request Slice
            logOutput.innerHTML += '<div>[INFO] 開始裁切處理...</div>';
            progressBar.style.width = '50%';
            
            const sliceRes = await fetch('/slice', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    video_filename: uploadData.video_filename,
                    srt_filename: uploadData.srt_filename,
                    ranges: ranges
                })
            });

            const sliceData = await sliceRes.json();
            
            if (!sliceRes.ok) {
                throw new Error(sliceData.message || '裁切失敗');
            }

            progressBar.style.width = '100%';
            logOutput.innerHTML += '<div>[INFO] 處理完成！</div>';
            logOutput.innerHTML += `<div class="text-success">[SUCCESS] 輸出檔案：${sliceData.files.join(', ')}</div>`;
            logOutput.innerHTML += `<div class="text-muted small">檔案位置：${sliceData.output_dir}</div>`;
            
            startSliceBtn.innerHTML = '<i class="bi bi-check-lg me-2"></i>完成';

        } catch (error) {
            console.error(error);
            logOutput.innerHTML += `<div class="text-danger">[ERROR] ${error.message}</div>`;
            startSliceBtn.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i>重試';
            progressBar.classList.add('bg-danger');
        } finally {
            startSliceBtn.disabled = false;
            setTimeout(() => {
                if (!startSliceBtn.innerHTML.includes('重試')) {
                    startSliceBtn.innerHTML = '<i class="bi bi-scissors me-2"></i>開始裁切';
                    progressBar.style.width = '0%';
                }
            }, 5000);
        }
    });
});
