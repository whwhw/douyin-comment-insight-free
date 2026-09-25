/* Shared homepage aggregation. Account summaries are evidence signals, not causal proof. */
(function () {
  'use strict';
  const primary = {
    songxiaoshuya: 'AI 创业与副业', ai_coder_wang: 'AI 工具与自动化',
    '78688074981': 'AI 工具与自动化', '61816395438': 'AI 工具与自动化',
    '23142962689': 'AI 工具与自动化', yulaoshiai: '企业 AI 应用',
    '90235775836': 'AI 内容创作', '607872315': '内容运营与增长',
    '78261563904': 'AI 内容创作', '55600015851': 'AI 工具与自动化',
    '97420239641': 'AI 工具与自动化', bdedu2099: '企业 AI 应用',
    captainconer: 'AI 内容创作', XiaoyuBoi: 'AI 工具与自动化',
    '71660790940': 'AI 内容创作', bdsxy166: '企业 AI 应用'
  };
  function category(row) {
    if (primary[row.accountId]) return primary[row.accountId];
    const lane = String(row.lane || '');
    if (/企业|获客/.test(lane)) return '企业 AI 应用';
    if (/创富|创业|副业|数字游民/.test(lane)) return 'AI 创业与副业';
    if (/视频|动漫|内容生产|创作/.test(lane)) return 'AI 内容创作';
    if (/公众号|运营|流量/.test(lane)) return '内容运营与增长';
    if (/工具|自动化|Codex|工作流|Skill|实操|部署/i.test(lane)) return 'AI 工具与自动化';
    return '待分类';
  }
  function aggregate(data) {
    const reports = Array.isArray(data.reports) ? data.reports : [];
    const groups = new Map();
    reports.forEach(row => { const name = category(row); if (!groups.has(name)) groups.set(name, []); groups.get(name).push(row); });
    const lanes = [...groups].sort((a,b) => b[1].length-a[1].length || a[0].localeCompare(b[0],'zh-CN'));
    const ready = reports.filter(r => r.status === 'completed' && r.summary);
    const themes = [
      {label:'共性需求',pattern:/安装|领取|获取|首次|实操|跑通|实战/,text:'把工具获取、安装与首次实操串成完整跟练。'},
      {label:'主要障碍',pattern:/成本|费用|门槛|排障|验收|失败|稳定|质量|画质|断句/,text:'成本、环境与质量边界不清楚，演示之后仍有执行障碍。'},
    ].map(t => ({...t, sources:ready.filter(r => t.pattern.test(r.summary))}));
    return {reports,ready,lanes,themes};
  }
  if (typeof module !== 'undefined') module.exports = {aggregate,category};
  if (typeof document === 'undefined') return;
  const data = window.COMMENT_INSIGHT_INDEX || {}, model = aggregate(data);
  function track(lane) {
    const value=String(lane||'');
    if (/企业|创业|创富|副业|获客/.test(value)) return 'business';
    if (/视频|动漫|内容生产|视觉/.test(value)) return 'content';
    if (/公众号|运营|流量/.test(value)) return 'growth';
    return 'tools';
  }
  function colorizeCards() {
    document.querySelectorAll('#cards .card').forEach(card=>{
      card.dataset.track=track(card.querySelector('.lane')?.textContent);
      const detailLink=card.querySelector('a.open:not(.disabled)');
      if(!detailLink)return;
      card.dataset.href=detailLink.getAttribute('href');
      card.setAttribute('role','link');
      card.setAttribute('tabindex','0');
      card.setAttribute('aria-label',`打开${card.querySelector('.name')?.textContent||'账号'}洞察`);
    });
  }
  colorizeCards();
  const cardsRoot=document.querySelector('#cards');
  if(cardsRoot){
    new MutationObserver(colorizeCards).observe(cardsRoot,{childList:true});
    cardsRoot.addEventListener('click',event=>{
      const card=event.target.closest('.card[data-href]');
      if(!card||event.target.closest('a,button,input,select,textarea'))return;
      location.href=card.dataset.href;
    });
    cardsRoot.addEventListener('keydown',event=>{
      const card=event.target.closest('.card[data-href]');
      if(!card||event.target!==card||!['Enter',' '].includes(event.key))return;
      event.preventDefault();location.href=card.dataset.href;
    });
  }
  const safe = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const link = row => /^[\w-]+\.html$/.test(row.file || '') ? row.file : null;
  const chart = document.querySelector('.lane-empty');
  if (chart) {
    const top = model.lanes.slice(0,5), max = Math.max(1,...top.map(([,rows])=>rows.length));
    chart.innerHTML = top.map(([name,rows])=>`<div class="lane-row"><span class="lane-name" title="${safe(rows.map(r=>r.displayName).join('、'))}">${safe(name)}</span><span class="lane-track"><span class="lane-fill" style="display:block;width:${rows.length/max*100}%"></span></span><b class="lane-count">${rows.length}</b></div>`).join('') || '暂无赛道数据';
    const caption = chart.parentElement.querySelector('.panel-title span');
    if (caption) caption.textContent = '每账号计一个主赛道';
    const note = document.createElement('div');note.className='run-note';
    note.textContent=`共 ${model.reports.length} 个账号 · ${model.lanes.length} 类${model.lanes.length>5?' · 仅展示前 5 类':''} · 悬停名称查看归类账号`;
    chart.after(note);
  }
  const panel = document.querySelector('.conclusion');
  if (!panel) return;
  panel.querySelector('.kicker').textContent='跨账号洞察';
  panel.querySelector('h3').textContent=model.themes[0].sources.length ? '从“看懂工具”到“完成真实任务”' : '当前样本仍需积累';
  const body=panel.querySelector('#conclusion');
  const list=document.createElement('div');list.id='conclusion';list.className='insight-findings';
  list.innerHTML=model.themes.map(t=>`<div class="insight-finding"><strong>${t.label}</strong><span>${t.sources.length?safe(t.text):'暂无足够的账号摘要信号。'}</span>${t.sources.length?`<details class="insight-sources"><summary>${t.sources.length} 个账号依据</summary><div>${t.sources.map(r=>link(r)?`<a href="${safe(link(r))}">${safe(r.displayName)} ↗</a>`:`<span>${safe(r.displayName)}</span>`).join('')}</div></details>`:''}</div>`).join('');
  body.replaceWith(list);
})();
