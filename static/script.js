class NotesManager {
    constructor() {
        this.currentImages = [];
        this.savedChapters = [];
        this.currentChapterName = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadSavedChapters(); // always fresh from backend
        this.updateUI();
    }

    setupEventListeners() {
        const chapterInput = document.getElementById('chapterName');
        chapterInput.addEventListener('input', () => this.validateForm());

        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const browseBtn = document.querySelector('.browse-btn');

        dropZone.addEventListener('click', () => fileInput.click());
        browseBtn.addEventListener('click', (e) => { e.stopPropagation(); fileInput.click(); });

        dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        dropZone.addEventListener('drop', (e) => this.handleDrop(e));
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        document.getElementById('processChapterBtn').addEventListener('click', () => this.processChapter());
        document.getElementById('clearBtn').addEventListener('click', () => this.clearCurrentChapter());

        document.getElementById('closeSuccessBtn').addEventListener('click', () => this.closeSuccessModal());
        document.getElementById('viewNotesBtn').addEventListener('click', () => this.viewNotes());
        document.getElementById('downloadNotesBtn')?.addEventListener('click', () => this.downloadNotes());
    }

    handleDragOver(e){ e.preventDefault(); document.getElementById('dropZone').classList.add('drag-over'); }
    handleDragLeave(e){ e.preventDefault(); document.getElementById('dropZone').classList.remove('drag-over'); }
    handleDrop(e){ e.preventDefault(); document.getElementById('dropZone').classList.remove('drag-over'); const files = Array.from(e.dataTransfer.files).filter(f=>f.type.startsWith('image/')); this.addImages(files); }
    handleFileSelect(e){ const files = Array.from(e.target.files); this.addImages(files); e.target.value=''; }

    addImages(files){
        files.forEach(file=>{
            const imageObj = {
                id: Date.now() + Math.random().toString(36).substr(2,9),
                file, name:file.name, size:this.formatFileSize(file.size),
                url: URL.createObjectURL(file),
                uploadDate: new Date().toISOString()
            };
            this.currentImages.push(imageObj);
        });
        this.updateImagePreview(); this.validateForm(); this.showNotification(`${files.length} image(s) added successfully!`,'success');
    }

    removeImage(imageId){
        const i = this.currentImages.findIndex(img=>img.id===imageId);
        if(i>-1){ URL.revokeObjectURL(this.currentImages[i].url); this.currentImages.splice(i,1); this.updateImagePreview(); this.validateForm(); }
    }

    updateImagePreview(){
        const preview = document.getElementById('imagePreview');
        const counter = document.querySelector('.image-counter');
        counter.textContent = `${this.currentImages.length} images selected`;
        if(this.currentImages.length===0){ preview.innerHTML=''; return; }
        preview.innerHTML = this.currentImages.map(image=>`
            <div class="image-item">
                <img src="${image.url}" alt="${image.name}" loading="lazy">
                <div class="image-info">
                    <div class="image-name">${image.name}</div>
                    <div class="image-size">${image.size}</div>
                </div>
                <button class="remove-image" onclick="notesManager.removeImage('${image.id}')" title="Remove image">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }

    async processChapter(){
        const chapterName = document.getElementById('chapterName').value.trim();
        if(!chapterName || this.currentImages.length===0){ this.showNotification('Please enter chapter name and add images!','error'); return; }

        const modal = document.getElementById('processModal'); modal.classList.remove('hidden'); this.currentChapterName = chapterName;

        try{
            const formData = new FormData();
            const chapterData = {
                chapters:[{
                    id: Date.now().toString(),
                    name: chapterName,
                    images: this.currentImages.map(img=>({id:img.id, name:img.name, size:img.size, uploadDate:img.uploadDate})),
                    imageCount: this.currentImages.length,
                    createdAt: new Date().toISOString()
                }]
            };
            formData.append('chaptersData', JSON.stringify(chapterData));
            this.currentImages.forEach(img=>formData.append(`image_${img.id}`, img.file));

            await this.simulateProcessing();

            const resp = await fetch('/process-chapter', { method:'POST', body: formData });
            const result = await resp.json();
            modal.classList.add('hidden');
            if(resp.ok){
                await this.loadSavedChapters();
                this.clearCurrentChapter();
                this.updateUI();
                this.showSuccessModal();
                this.showNotification(`Chapter "${chapterName}" processed successfully!`,'success');
            }else{
                this.showNotification(result.error || 'Failed to process chapter','error');
            }
        }catch(err){
            modal.classList.add('hidden');
            console.error(err);
            this.showNotification('Failed to process chapter. Please try again.','error');
        }
    }

    async regenerateNotes(chapterName){
        if(!confirm(`Regenerate notes for "${chapterName}"?`)) return;
        const modal = document.getElementById('processModal'); modal.classList.remove('hidden'); this.currentChapterName = chapterName;
        try{
            await this.simulateProcessing();
            const resp = await fetch('/regenerate-notes',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({chapter_name: chapterName})});
            const result = await resp.json();
            modal.classList.add('hidden');
            if(resp.ok){
                this.showSuccessModal();
                this.showNotification(`Notes regenerated for "${chapterName}"!`,'success');
                await this.loadSavedChapters();
            }else{
                this.showNotification(result.error || 'Failed to regenerate notes','error');
            }
        }catch(err){
            modal.classList.add('hidden');
            console.error(err);
            this.showNotification('Failed to regenerate notes. Please try again.','error');
        }
    }

    async downloadNotesFile(chapterName){
        try{
            const resp = await fetch(`/download-notes/${encodeURIComponent(chapterName)}`, { headers: { 'Accept': 'application/pdf' } });
            if(!resp.ok){ this.showNotification('Failed to download notes','error'); return; }
            const blob = await resp.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${chapterName}_notes.pdf`; // FIX: ensure .pdf extension
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            this.showNotification(`PDF downloaded for "${chapterName}"!`,'success');
        }catch(err){
            console.error(err);
            this.showNotification('Failed to download notes','error');
        }
    }

    async viewNotesFile(chapterName){
        try{
            const response = await fetch(`/view-notes/${encodeURIComponent(chapterName)}`);
            const result = await response.json();
            if(response.ok){ this.showNotesModal(result.chapter_name, result.content); }
            else{ this.showNotification(result.error || 'Failed to view notes','error'); }
        }catch(err){ console.error(err); this.showNotification('Failed to view notes','error'); }
    }

    showNotesModal(chapterName, content){
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content" style="max-width: 800px; max-height: 80vh;">
                <div class="modal-header">
                    <h3><i class="fas fa-file-text"></i> Notes: ${chapterName}</h3>
                    <button class="close-modal" style="background:none;border:none;color:var(--text-muted);font-size:1.5rem;cursor:pointer;">&times;</button>
                </div>
                <div class="modal-body" style="overflow-y:auto; max-height:60vh;">
                    <pre style="white-space:pre-wrap; color:var(--text-primary); font-family:monospace; font-size:0.9rem;">${content}</pre>
                </div>
                <div style="margin-top:1rem; text-align:center;">
                    <button class="btn btn-secondary close-modal">Close</button>
                </div>
            </div>`;
        document.body.appendChild(modal);
        modal.querySelectorAll('.close-modal, .modal-overlay').forEach(btn=>{
            btn.addEventListener('click', ()=> document.body.removeChild(modal));
        });
    }

    async deleteChapter(chapterName){
        if(!confirm('Are you sure you want to delete this chapter?')) return;
        try{
            const resp = await fetch('/delete-chapter', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({chapter_name: chapterName}) });
            const result = await resp.json();
            if(resp.ok){ await this.loadSavedChapters(); this.updateUI(); this.showNotification('Chapter deleted successfully!','success'); }
            else{ this.showNotification(result.error || 'Failed to delete chapter','error'); }
        }catch(err){ console.error(err); this.showNotification('Failed to delete chapter. Please try again.','error'); }
    }

    clearCurrentChapter(){
        this.currentImages.forEach(img=>URL.revokeObjectURL(img.url));
        this.currentImages = [];
        document.getElementById('chapterName').value = '';
        this.updateImagePreview();
        this.validateForm();
    }

    async loadSavedChapters(){
        try{
            const resp = await fetch('/get-chapters');
            const result = await resp.json();
            if(resp.ok){ this.savedChapters = result.chapters; this.updateChaptersList(); this.updateUI(); }
        }catch(err){ console.error('Load chapters error:', err); }
    }

    updateChaptersList(){
        const list = document.getElementById('chaptersList');
        if(this.savedChapters.length===0){
            list.innerHTML = `
                <div class="text-center" style="grid-column:1 / -1; padding:2rem; color:var(--text-muted);">
                    <i class="fas fa-book" style="font-size:3rem; margin-bottom:1rem; opacity:0.5;"></i>
                    <p>No chapters processed yet. Add your first chapter above!</p>
                </div>`;
            return;
        }
        list.innerHTML = this.savedChapters.map(ch=>`
            <div class="chapter-card">
                <div class="chapter-header">
                    <div>
                        <div class="chapter-title">${ch.name}</div>
                        <div class="chapter-meta">
                            ${ch.image_count} images
                            ${ch.has_notes ? '• <i class="fas fa-file-text" style="color: var(--success-color);"></i> Notes Ready' : ''}
                            ${ch.has_pdf ? ' • <i class="fas fa-file-pdf" style="color:#ff3b30;"></i> PDF Ready' : ''}
                            ${ch.notes_date ? `<br><small>Notes: ${ch.notes_date}</small>` : ''}
                        </div>
                    </div>
                    <button class="delete-chapter" onclick="notesManager.deleteChapter('${ch.name}')" title="Delete chapter">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="chapter-actions">
                    <button class="btn btn-regenerate" onclick="notesManager.regenerateNotes('${ch.name}')" title="Regenerate notes">
                        <i class="fas fa-redo"></i> Regenerate Notes
                    </button>
                    ${ch.has_pdf ? `
                        <button class="btn btn-download" onclick="notesManager.downloadNotesFile('${ch.name}')" title="Download notes">
                            <i class="fas fa-download"></i> Download
                        </button>
                    ` : ''}
                    ${ch.has_notes ? `
                        <button class="btn btn-view" onclick="notesManager.viewNotesFile('${ch.name}')" title="View notes">
                            <i class="fas fa-eye"></i> View
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    async simulateProcessing(){
        const steps = [
            { id:'step1', text:'Analyzing Images...', duration:900 },
            { id:'step2', text:'Processing Questions...', duration:1200 },
            { id:'step3', text:'Generating Notes...', duration:1500 },
            { id:'step4', text:'Finalizing...', duration:700 }
        ];
        const progressFill = document.getElementById('progressFill');
        const progressPercent = document.getElementById('progressPercent');
        const statusText = document.getElementById('processStatus');

        for(let i=0;i<steps.length;i++){
            const step = steps[i];
            const stepEl = document.getElementById(step.id);
            statusText.textContent = step.text;
            stepEl.classList.add('active');
            stepEl.querySelector('i').className = 'fas fa-spinner fa-spin';
            const target = ((i+1)/steps.length)*100;
            await this.animateProgress(progressFill, progressPercent, target);
            await new Promise(r=>setTimeout(r, step.duration));
            stepEl.classList.remove('active');
            stepEl.classList.add('completed');
            stepEl.querySelector('i').className = 'fas fa-check-circle';
        }
        statusText.textContent = 'Processing completed successfully!';
    }

    async animateProgress(el, textEl, target){
        return new Promise(resolve=>{
            let current = parseFloat(el.style.width)||0;
            const inc = (target-current)/20;
            const tick = ()=>{
                current += inc;
                if(current>=target){ current = target; el.style.width = `${current}%`; textEl.textContent = `${Math.round(current)}%`; resolve(); }
                else { el.style.width = `${current}%`; textEl.textContent = `${Math.round(current)}%`; requestAnimationFrame(tick); }
            };
            requestAnimationFrame(tick);
        });
    }

    showSuccessModal(){ document.getElementById('successModal').classList.remove('hidden'); }
    closeSuccessModal(){
        const modal = document.getElementById('successModal'); modal.classList.add('hidden');
        document.getElementById('progressFill').style.width='0%';
        document.getElementById('progressPercent').textContent='0%';
        document.querySelectorAll('.step').forEach(s=>{ s.classList.remove('active','completed'); s.querySelector('i').className='fas fa-circle'; });
    }
    viewNotes(){ if(this.currentChapterName){ this.viewNotesFile(this.currentChapterName); } this.closeSuccessModal(); }
    downloadNotes(){ if(this.currentChapterName){ this.downloadNotesFile(this.currentChapterName); } this.closeSuccessModal(); }

    validateForm(){
        const chapterName = document.getElementById('chapterName').value.trim();
        const hasImages = this.currentImages.length>0;
        document.getElementById('processChapterBtn').disabled = !(chapterName && hasImages);
    }
    updateUI(){
        const totalChapters = this.savedChapters.length;
        const totalImages = this.savedChapters.reduce((sum,ch)=>sum + (ch.image_count||0), 0);
        document.getElementById('chaptersCount').textContent = `${totalChapters} chapter${totalChapters!==1?'s':''}`;
        document.getElementById('totalImages').textContent = `${totalImages} total images`;
    }
    formatFileSize(bytes){ if(bytes===0) return '0 Bytes'; const k=1024, sizes=['Bytes','KB','MB','GB']; const i=Math.floor(Math.log(bytes)/Math.log(k)); return parseFloat((bytes/Math.pow(k,i)).toFixed(2))+' '+sizes[i]; }

    showNotification(message, type='info'){
        const n = document.createElement('div');
        n.style.cssText = `
            position:fixed; top:20px; right:20px; padding:1rem 1.5rem; border-radius:8px; color:white;
            font-weight:500; z-index:1001; box-shadow:var(--shadow-lg); transform:translateX(100%); transition:transform .3s; max-width:300px;
        `;
        const colors = { success:'#48bb78', error:'#f56565', info:'#4299e1', warning:'#ed8936' };
        n.style.background = colors[type] || colors.info;
        n.innerHTML = `<div style="display:flex; align-items:center; gap:.5rem;">
            <i class="fas fa-${type==='success'?'check-circle':type==='error'?'exclamation-circle':'info-circle'}"></i>
            <span>${message}</span></div>`;
        document.body.appendChild(n);
        setTimeout(()=>{ n.style.transform='translateX(0)'; },100);
        setTimeout(()=>{ n.style.transform='translateX(100%)'; setTimeout(()=>{ n.remove(); },300); },4000);
    }
}
const notesManager = new NotesManager();
['dragenter','dragover','dragleave','drop'].forEach(ev=>{
    document.addEventListener(ev,(e)=>{ e.preventDefault(); e.stopPropagation(); },false);
});
document.addEventListener('click',(e)=>{ if(e.target.classList.contains('modal-overlay')){ e.target.parentElement.classList.add('hidden'); }});