import React, { useEffect, useMemo, useState } from 'react'
import { Activity, ArrowRight, Check, ChevronRight, Code2, Download, FileCode2, FileText, Github, Layers3, LoaderCircle, Rocket, ShieldCheck, Upload, WandSparkles, XCircle } from 'lucide-react'

const api = async (url, options={}) => {
  const response = await fetch(url, {credentials:'include', ...options})
  const data = response.headers.get('content-type')?.includes('application/json') ? await response.json() : null
  if (!response.ok) throw new Error(data?.detail || `Request failed (${response.status})`)
  return data
}
const initialSpec = `# Few-Shot Learning Framework for Rare-Class Detection in Imbalanced Industrial Datasets

Build a reproducible machine learning framework to detect rare defect classes in imbalanced industrial datasets. Include dataset validation, preprocessing, class-imbalance strategies, few-shot learning baselines, evaluation metrics, experiment configuration, API or CLI entry point, and documentation. Keep data paths configurable and do not include private datasets.`

export default function App() {
  const [spec, setSpec] = useState(initialSpec)
  const [language, setLanguage] = useState('Python')
  const [framework, setFramework] = useState('FastAPI')
  const [projectName, setProjectName] = useState('rare-class-detection')
  const [project, setProject] = useState(null)
  const [files, setFiles] = useState([])
  const [selected, setSelected] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [gh, setGh] = useState({connected:false,username:''})
  const [repos, setRepos] = useState([])
  const [mode, setMode] = useState('create')
  const [repo, setRepo] = useState('rare-class-detection')
  const [description, setDescription] = useState('Few-shot learning framework for rare-class detection in imbalanced industrial datasets.')
  const [privateRepo, setPrivateRepo] = useState(true)
  const [branch, setBranch] = useState('main')
  const [confirmed, setConfirmed] = useState(false)
  const [published, setPublished] = useState(null)

  useEffect(() => {
    api('/api/github/status').then(setGh).catch(()=>{})
    const params = new URLSearchParams(location.search)
    if (params.has('github_connected')) { setNotice('GitHub connected successfully.'); history.replaceState({}, '', location.pathname) }
    if (params.has('github_error')) { setError('GitHub authorization was cancelled or denied.'); history.replaceState({}, '', location.pathname) }
  }, [])
  const currentFile = useMemo(() => files.find(f=>f.path===selected), [files, selected])
  const folders = useMemo(() => [...new Set(files.map(f=>f.path.split('/').slice(0,-1).join('/')).filter(Boolean))].sort(), [files])

  async function uploadFile(file) {
    if (!file) return
    setError(''); setBusy('upload')
    try {
      const form = new FormData(); form.append('file', file)
      const data = await api('/api/projects/analyze-upload', {method:'POST', body:form})
      setSpec(prev => `${prev.trim()}\n\n--- Uploaded specification: ${data.filename} ---\n${data.specification}`)
      setNotice(`Extracted ${data.characters} characters from ${data.filename}.`)
    } catch(e) { setError(e.message) } finally { setBusy('') }
  }
  async function analyze() {
    setError(''); setNotice(''); setBusy('analyze')
    try { setAnalysis(await api('/api/projects/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({specification:spec})})) }
    catch(e){setError(e.message)} finally{setBusy('')}
  }
  async function generate() {
    setError(''); setNotice(''); setPublished(null); setBusy('generate')
    try {
      const data = await api('/api/projects/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({specification:spec,language,framework,project_name:projectName})})
      const result = await api(`/api/projects/${data.project_id}/files`)
      setProject(data); setFiles(result.files); setSelected(result.files[0]?.path || ''); setConfirmed(false)
      setNotice(`Generated ${data.file_count} files. Review the files before publishing.`)
    } catch(e){setError(e.message)} finally{setBusy('')}
  }
  async function connectGithub() {
    setError('')
    try { const response = await fetch('/api/github/login',{credentials:'include',redirect:'manual'}); if (response.status===503) { const d=await response.json(); throw new Error(d.detail) } location.href='/api/github/login' }
    catch(e){setError(e.message)}
  }
  async function loadRepos() {
    setError(''); setBusy('repos')
    try { const data=await api('/api/github/repositories'); setRepos(data); if(data.length) {setMode('existing'); setRepo(data[0].name); setBranch(data[0].default_branch || 'main')} }
    catch(e){setError(e.message)} finally{setBusy('')}
  }
  async function publish() {
    if (!project) return
    setError(''); setNotice(''); setPublished(null); setBusy('publish')
    try {
      const data=await api('/api/github/publish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_id:project.project_id,mode,repository:repo,description,private:privateRepo,branch,confirmed})})
      setPublished(data); setNotice(`Published ${data.files_published} files to GitHub.`)
    } catch(e){setError(e.message)} finally{setBusy('')}
  }
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Layers3 size={21}/></div><div><strong>APB Studio</strong><small>AI PROJECT BUILDER</small></div></div>
      <div className="side-label">WORKSPACE</div>
      <a className="nav active"><Activity size={17}/> Project builder</a>
      <a className="nav" href="#files"><Code2 size={17}/> Generated files</a>
      <a className="nav" href="#publish"><Github size={17}/> GitHub publish</a>
      <div className="sidebar-bottom"><div className="secure-icon"><ShieldCheck size={17}/></div><strong>Built with security in mind</strong><p>Provider keys stay on the backend. Review files before publishing.</p><span className="status-pill"><i/> API workspace</span></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumb">Workspace <ChevronRight size={14}/> <b>New project</b></div><div className="top-right"><span className="live-dot"/> <span>Local workspace</span><div className="avatar">AP</div></div></header>
      <div className="content">
        <section className="hero"><div><div className="eyebrow"><WandSparkles size={14}/> FROM IDEA TO CODEBASE</div><h1>Build something<br/><span>remarkable.</span></h1><p>Turn a project specification into a structured codebase, then download it or publish it to GitHub.</p></div><div className="hero-art"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="hero-core"><Code2 size={36}/></div><span className="float-chip chip-one">{"</>"}</span><span className="float-chip chip-two"><Layers3 size={17}/></span><span className="float-chip chip-three"><Rocket size={17}/></span></div></section>
        {error && <div className="alert error"><XCircle size={18}/><span>{error}</span><button onClick={()=>setError('')} aria-label="Dismiss error">×</button></div>}
        {notice && <div className="alert success"><Check size={18}/><span>{notice}</span><button onClick={()=>setNotice('')} aria-label="Dismiss message">×</button></div>}
        <div className="section-heading"><div><span className="step">01</span><div><h2>Define your project</h2><p>Describe what you want to build. Be specific about features and expected outputs.</p></div></div><span className="required">REQUIRED</span></div>
        <section className="panel spec-panel">
          <div className="panel-top"><label htmlFor="spec">PROJECT SPECIFICATION</label><span><span className="live-dot"/> {spec.length.toLocaleString()} characters</span></div>
          <textarea id="spec" value={spec} onChange={e=>setSpec(e.target.value)} placeholder="Describe your project, requirements, features, and expected output…" />
          <div className="spec-footer"><label className="upload-btn"><Upload size={16}/>{busy==='upload'?'Extracting…':'Upload brief'}<input type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp,.bmp" onChange={e=>uploadFile(e.target.files?.[0])} hidden/></label><span className="muted">PDF, DOCX, TXT, PNG, JPG · max 10 MB</span><button className="text-btn" onClick={analyze} disabled={!spec.trim()||!!busy}>{busy==='analyze'?<LoaderCircle className="spin" size={15}/>:<FileText size={15}/>} Analyze requirements</button></div>
          {analysis && <div className="analysis-box"><strong>{analysis.summary}</strong>{analysis.requirements?.length>0&&<ul>{analysis.requirements.slice(0,8).map((x,i)=><li key={i}>{typeof x==='string'?x:JSON.stringify(x)}</li>)}</ul>}{analysis.message&&<p>{analysis.message}</p>}</div>}
          <div className="form-grid"><div><label htmlFor="pname">PROJECT NAME</label><input id="pname" value={projectName} onChange={e=>setProjectName(e.target.value)} placeholder="my-project"/></div><div><label htmlFor="language">LANGUAGE</label><select id="language" value={language} onChange={e=>setLanguage(e.target.value)}>{['Python','JavaScript','TypeScript','Java','C++','Go','Rust'].map(x=><option key={x}>{x}</option>)}</select></div><div><label htmlFor="framework">FRAMEWORK / STACK</label><select id="framework" value={framework} onChange={e=>setFramework(e.target.value)}>{['FastAPI','Flask','Django','React + Vite','Next.js','Node.js + Express','Spring Boot','PyTorch','scikit-learn','None / CLI'].map(x=><option key={x}>{x}</option>)}</select></div></div>
          <div className="generate-row"><div className="hint"><span className="hint-icon"><WandSparkles size={17}/></span><span><b>AI-powered generation</b><small>Source files, setup docs and dependency manifests</small></span></div><button className="primary-btn" onClick={generate} disabled={!!busy||spec.trim().length<10}>{busy==='generate'?<><LoaderCircle className="spin" size={17}/> Generating project…</>:<>Generate project <ArrowRight size={17}/></>}</button></div>
        </section>
        <div id="files" className="section-heading"><div><span className="step">02</span><div><h2>Explore your codebase</h2><p>Browse the generated file tree and inspect source code before downloading or publishing.</p></div></div>{project&&<span className="count-pill">{files.length} FILES</span>}</div>
        <section className="panel file-panel">
          <div className="file-toolbar"><div className="file-toolbar-title"><FileCode2 size={17}/><strong>{project?.name || 'Your project files'}</strong><span className="branch-pill">main</span></div><div className="file-actions"><button className="secondary-btn" onClick={()=>project&&window.open(`/api/projects/${project.project_id}/download`,'_blank')} disabled={!project}><Download size={15}/> Download ZIP</button></div></div>
          <div className="explorer">
            <div className="tree"><div className="tree-label">EXPLORER <span>{files.length}</span></div>{!files.length?<div className="empty-tree"><Code2 size={23}/><p>Your generated files will appear here.</p></div>:files.map(f=><button key={f.path} className={`tree-file ${selected===f.path?'selected':''}`} onClick={()=>setSelected(f.path)} title={f.path}><FileIcon path={f.path}/><span>{f.path}</span></button>)}</div>
            <div className="code-area"><div className="code-header"><span><FileCode2 size={14}/>{currentFile?.path || 'No file selected'}</span>{currentFile&&<span>{currentFile.size.toLocaleString()} bytes</span>}</div>{currentFile?<pre className="code"><code>{currentFile.content}</code></pre>:<div className="code-empty"><Code2 size={34}/><b>Nothing to preview yet</b><p>Generate a project to explore its source files.</p></div>}</div>
          </div>
          {project&&<div className="file-footer"><span><Check size={15}/> Files stored in this server session</span><span>ZIP excludes blocked paths</span></div>}
        </section>
        <div id="publish" className="section-heading"><div><span className="step">03</span><div><h2>Publish to GitHub</h2><p>Authorize access, select a repository, and review the publish action.</p></div></div><span className={`connection ${gh.connected?'connected':''}`}><i/>{gh.connected?`Connected · ${gh.username}`:'Not connected'}</span></div>
        <section className="panel publish-panel">
          <div className="github-banner"><div className="github-icon"><Github size={25}/></div><div><h3>{gh.connected?'GitHub account connected':'Your code, in your repository'}</h3><p>{gh.connected?`Authorized as @${gh.username}. Choose a repository below.`:'Connect through GitHub OAuth. Your password is never requested by this app.'}</p></div>{!gh.connected?<button className="secondary-btn" onClick={connectGithub}><Github size={16}/> Connect GitHub</button>:<button className="secondary-btn" onClick={loadRepos} disabled={!!busy}>{busy==='repos'?<LoaderCircle className="spin" size={15}/>:<Activity size={15}/>} Load repositories</button>}</div>
          <div className="repo-form">
            <div className="mode-toggle"><button className={mode==='create'?'chosen':''} onClick={()=>setMode('create')}>Create new repository</button><button className={mode==='existing'?'chosen':''} onClick={()=>setMode('existing')}>Use existing repository</button></div>
            <div className="form-grid repo-grid"><div><label htmlFor="repo">REPOSITORY NAME</label>{mode==='existing'&&repos.length>0?<select id="repo" value={repo} onChange={e=>{setRepo(e.target.value);const r=repos.find(x=>x.name===e.target.value);if(r)setBranch(r.default_branch||'main')}}>{repos.map(r=><option key={r.id} value={r.name}>{r.name}{r.private?' · private':''}</option>)}</select>:<input id="repo" value={repo} onChange={e=>setRepo(e.target.value)} placeholder="my-new-project"/>}</div><div><label htmlFor="branch">TARGET BRANCH</label><input id="branch" value={branch} onChange={e=>setBranch(e.target.value)} placeholder="main"/></div></div>
            {mode==='create'&&<><div className="field"><label htmlFor="description">DESCRIPTION</label><input id="description" value={description} onChange={e=>setDescription(e.target.value)} maxLength={350}/></div><label className="check-row"><input type="checkbox" checked={privateRepo} onChange={e=>setPrivateRepo(e.target.checked)}/> Private repository <small>Only you and authorized collaborators can access it.</small></label></>}
            <div className="publish-review"><div><ShieldCheck size={18}/><div><b>Review before publishing</b><p>Secret-like files are filtered. Existing paths may be updated by the commit.</p></div></div><label className="check-row confirm"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/> I reviewed the files and confirm this GitHub publish action.</label></div>
            <button className="publish-btn" onClick={publish} disabled={!project||!gh.connected||!confirmed||!repo.trim()||!branch.trim()||!!busy}>{busy==='publish'?<><LoaderCircle className="spin" size={17}/> Publishing to GitHub…</>:<><Rocket size={17}/> Publish project <ArrowRight size={17}/></>}</button>
            {!project&&<p className="form-note">Generate a project before publishing.</p>}
            {published&&<div className="published-result"><Check size={18}/><div><b>GitHub confirmed the publish</b><p>{published.files_published} files committed · {published.branch}</p><a href={published.repository_url} target="_blank" rel="noreferrer">{published.repository_url} <ArrowRight size={14}/></a></div></div>}
          </div>
        </section>
        <footer><span>APB Studio · AI Project Builder</span><span>Secure by design <ShieldCheck size={14}/></span></footer>
      </div>
    </main>
  </div>
}
function FileIcon({path}) {
  const ext=path.split('.').pop().toLowerCase()
  const color=ext==='py'?'#63c5a4':ext==='js'||ext==='jsx'?'#e7c46b':ext==='json'?'#c29cf3':ext==='md'?'#8ca9ff':'#9ba7bd'
  return <FileCode2 size={15} color={color}/>
}
