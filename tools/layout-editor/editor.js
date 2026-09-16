const canvas = document.querySelector('#canvas');
const items = [...document.querySelectorAll('.movable')];
const gridToggle = document.querySelector('#gridToggle');
const snapToggle = document.querySelector('#snapToggle');
const selectionName = document.querySelector('#selectionName');
const inputs = {
  x: document.querySelector('#xInput'), y: document.querySelector('#yInput'),
  w: document.querySelector('#wInput'), h: document.querySelector('#hInput'),
  r: document.querySelector('#rInput'), s: document.querySelector('#sInput'),
};
let selected = null;
let action = null;
let z = 10;
const GRID = 8;

const defaults = Object.fromEntries(items.map(el => [el.dataset.id, readData(el)]));
items.forEach((el, index) => { el.style.zIndex = String(index + 1); apply(el); });

gridToggle.addEventListener('change', () => canvas.classList.toggle('grid-on', gridToggle.checked));
document.querySelector('#resetButton').addEventListener('click', reset);
document.querySelector('#exportButton').addEventListener('click', exportLayout);
document.querySelector('#importInput').addEventListener('change', importLayout);
document.querySelector('#frontButton').addEventListener('click', () => { if (selected) selected.style.zIndex = String(++z); });
document.querySelector('#centerButton').addEventListener('click', centerSelected);

for (const [key, input] of Object.entries(inputs)) {
  input.addEventListener('change', () => {
    if (!selected) return;
    const value = Number(input.value);
    if (!Number.isFinite(value)) return;
    if (key === 's') selected.dataset.s = String(Math.min(2, Math.max(.25, value)));
    else selected.dataset[key] = String(value);
    apply(selected); syncInspector();
  });
}

items.forEach(el => {
  el.addEventListener('pointerdown', event => {
    select(el);
    const resizing = event.target.classList.contains('resize');
    action = {
      type: resizing ? 'resize' : 'drag',
      pointerId: event.pointerId,
      startX: event.clientX, startY: event.clientY,
      x: num(el, 'x'), y: num(el, 'y'), w: num(el, 'w'), h: num(el, 'h'),
    };
    el.setPointerCapture(event.pointerId);
    event.preventDefault();
  });
  el.addEventListener('pointermove', event => {
    if (!action || action.pointerId !== event.pointerId) return;
    const scaleX = canvas.clientWidth / 1440;
    const scaleY = canvas.clientHeight / 810;
    const dx = (event.clientX - action.startX) / scaleX;
    const dy = (event.clientY - action.startY) / scaleY;
    if (action.type === 'drag') {
      el.dataset.x = String(clamp(snap(action.x + dx), 0, 1440 - num(el,'w')));
      el.dataset.y = String(clamp(snap(action.y + dy), 0, 810 - num(el,'h')));
    } else {
      el.dataset.w = String(clamp(snap(action.w + dx), 40, 1440 - num(el,'x')));
      el.dataset.h = String(clamp(snap(action.h + dy), 40, 810 - num(el,'y')));
    }
    apply(el); syncInspector();
  });
  el.addEventListener('pointerup', event => {
    if (action?.pointerId === event.pointerId) action = null;
  });
});

function select(el) {
  selected?.classList.remove('selected');
  selected = el;
  el.classList.add('selected');
  selectionName.textContent = el.dataset.id;
  syncInspector();
}
function syncInspector() {
  if (!selected) return;
  for (const key of ['x','y','w','h','r']) inputs[key].value = String(Math.round(num(selected,key)));
  inputs.s.value = selected.dataset.s || '1';
}
function apply(el) {
  const x = num(el,'x'), y = num(el,'y'), w = num(el,'w'), h = num(el,'h'), r = num(el,'r');
  const s = Number(el.dataset.s || 1);
  el.style.left = `${x}px`; el.style.top = `${y}px`; el.style.width = `${w}px`; el.style.height = `${h}px`;
  el.style.transform = `rotate(${r}deg) scale(${s})`;
}
function readData(el) {
  return { x:num(el,'x'), y:num(el,'y'), w:num(el,'w'), h:num(el,'h'), r:num(el,'r'), s:Number(el.dataset.s || 1), z:Number(el.style.zIndex || 1) };
}
function num(el,key){ return Number(el.dataset[key] || 0); }
function snap(value){ return snapToggle.checked ? Math.round(value/GRID)*GRID : Math.round(value); }
function clamp(value,min,max){ return Math.min(max,Math.max(min,value)); }
function centerSelected(){ if(!selected)return; selected.dataset.x=String((1440-num(selected,'w'))/2); selected.dataset.y=String((810-num(selected,'h'))/2); apply(selected); syncInspector(); }
function reset(){ items.forEach((el,index)=>{ const d=defaults[el.dataset.id]; Object.entries(d).forEach(([k,v])=>{ if(k==='z') el.style.zIndex=String(index+1); else el.dataset[k]=String(v); }); apply(el); }); if(selected) syncInspector(); }
function buildLayout(){
  return {
    schema: 'protean.layout/v1', canvas:{width:1440,height:810,grid:GRID},
    elements:Object.fromEntries(items.map(el => [el.dataset.id,{...readData(el), z:Number(el.style.zIndex || 1)}])),
    deferred:{spriteMode:true},
  };
}
function exportLayout(){ const blob=new Blob([JSON.stringify(buildLayout(),null,2)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='layout.json'; a.click(); setTimeout(()=>URL.revokeObjectURL(a.href),1000); }
async function importLayout(event){
  const file=event.target.files?.[0]; if(!file)return;
  try{ const data=JSON.parse(await file.text()); if(data.schema!=='protean.layout/v1'||!data.elements) throw new Error('Unsupported layout schema');
    for(const el of items){ const d=data.elements[el.dataset.id]; if(!d)continue; for(const key of ['x','y','w','h','r','s']) if(Number.isFinite(Number(d[key]))) el.dataset[key]=String(d[key]); if(Number.isFinite(Number(d.z))) el.style.zIndex=String(d.z); apply(el); }
    if(selected)syncInspector();
  }catch(error){ alert(`Could not import layout: ${error.message}`); }
  event.target.value='';
}
select(document.querySelector('[data-id="chat"]'));
