const fs=require('fs'),path=require('path'),vm=require('vm');
const root=path.resolve(__dirname,'..'), site=process.argv.includes('--site')?path.resolve(process.argv[process.argv.indexOf('--site')+1]):path.join(root,'workspace/site');
const rows=JSON.parse(fs.readFileSync(path.join(site,'comment-insight-index.json'))).reports;
let scripts=0,resources=0;
for(const name of ['comment-insight-index.html',...rows.map(r=>r.file)]){
 const html=fs.readFileSync(path.join(site,name),'utf8');
 for(const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)){
  if(!m[1].includes('application/json') && m[2].trim()){new vm.Script(m[2],{filename:name});scripts++;}
 }
 for(const m of html.matchAll(/(?:src|href)=["'](assets\/[^"']+)["']/g)){
  if(m[1].includes('${'))continue; const file=path.join(site,m[1].split('?')[0]);if(!fs.existsSync(file))throw Error('Missing '+file);resources++;
 }
 if(/<style\b/.test(html))throw Error('Inline style remains '+name);
}
for(const name of ['index.css','report.css']){
 const css=fs.readFileSync(path.join(root,'assets/ui',name),'utf8');
 for(const m of css.matchAll(/url\(["']?([^\)"']+)["']?\)/g)){
  if(/^(data:|https?:|#)/.test(m[1]))continue;
  if(!fs.existsSync(path.resolve(site,'assets/ui',m[1])))throw Error('Missing CSS resource '+m[1]);
 }
}
console.log(JSON.stringify({pages:rows.length+1,inlineScriptsParsed:scripts,resourceReferencesChecked:resources}));
