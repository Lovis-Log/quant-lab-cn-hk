"""Inline, local-search security selection; only normalized codes enter UI state."""

import sqlite3

import streamlit as st

from quant_lab import names
from quant_lab.navigation import comparison_selection
from quant_lab.securities import security_directory
from quant_lab.storage import list_watchlist


CSS = """
.ql-security-picker{font:13px 'Microsoft YaHei UI','Segoe UI',sans-serif;color:#E8EBEE;min-width:0}
*{box-sizing:border-box}.label{display:block;font-size:12px;color:#929AA3;margin:0 0 7px}
.field{display:flex;align-items:center;gap:6px;border:1px solid #454D56;border-radius:4px;background:#22262A;padding:6px 8px;min-height:38px}
.field:focus-within{border-color:#78A7DB}.values{display:flex;flex-wrap:wrap;align-items:center;gap:5px;flex:1;min-width:0}
.chip{display:inline-flex;align-items:center;gap:5px;background:#293A4B;border-radius:3px;padding:3px 6px;max-width:100%}
.chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.chip button{background:transparent;border:0;color:#B6C9DD;padding:0 2px;cursor:pointer}
input{font:inherit;color:inherit;background:transparent;border:0;outline:0;flex:1;min-width:75px;width:130px;padding:2px}
button{font:inherit}.arrow{align-self:stretch;width:28px;flex:0 0 28px;border:0;background:transparent;color:#CAD2DC;cursor:pointer;font-size:19px;border-radius:3px}
.arrow:hover{background:#303940}.arrow[aria-expanded=true]{rotate:180deg}.candidates{margin-top:5px;border:1px solid #454D56;border-radius:4px;background:#1C1F22;max-height:250px;overflow:auto;padding:4px}
.candidates[hidden]{display:none}.option{width:100%;display:flex;align-items:center;text-align:left;gap:8px;background:transparent;color:#E8EBEE;border:0;border-radius:3px;padding:8px;cursor:pointer}
.option:hover,.option.focused{background:#293A4B}.option[aria-selected=true]{color:#A8C9ED}.check{width:14px;flex:0 0 14px}.message{font-size:11px;color:#929AA3;padding:6px 8px}.count{margin-top:5px;font-size:11px;color:#929AA3}
button:focus-visible{outline:2px solid #78A7DB;outline-offset:1px}
"""

JS = r"""
export default function(component) {
  const {parentElement,data,setStateValue} = component;
  const root = parentElement.querySelector('.ql-security-picker');
  const previous = root._picker;
  if (previous) { previous.update(data); return; }
  root.innerHTML = '<label class="label"></label><div class="field"><div class="values"></div><button type="button" class="arrow" aria-label="展开股票候选" aria-expanded="false">⌄</button></div><div class="candidates" role="listbox" hidden></div><div class="count" aria-live="polite"></div>';
  const label=root.querySelector('.label'), values=root.querySelector('.values'), arrow=root.querySelector('.arrow');
  const list=root.querySelector('.candidates'), count=root.querySelector('.count');
  const input=document.createElement('input'); input.type='text'; input.autocomplete='off'; input.setAttribute('role','combobox');
  input.setAttribute('aria-autocomplete','list');
  const saved=root._pickerUi||{};
  let config=data, selected=[...data.selected], opened=!!saved.opened, query=saved.query||'', focused=-1, filtered=[];
  let labels=new Map(config.options.map(item=>[item.code,item.name]));
  const text = code => `${code}（${labels.get(code)||'名称暂不可用'}）`;
  const setOpen = value => {
    opened=value; arrow.setAttribute('aria-expanded',String(value)); input.setAttribute('aria-expanded',String(value));
    arrow.setAttribute('aria-label',value?'收起股票候选':'展开股票候选'); list.hidden=!value;
    if(value) renderList();
  };
  const emit = () => { renderValues(); renderList(); setStateValue('selection',[...selected]); };
  const choose = code => {
    if(config.multiple) {
      if(selected.includes(code)) selected=selected.filter(value=>value!==code);
      else if(selected.length<10) selected.push(code);
      else { count.textContent='最多选择10只股票，请先移除部分股票'; return; }
    } else selected=[code];
    query=''; input.value=''; focused=-1; emit(); if(!config.multiple) setOpen(false);
    input.focus({preventScroll:true});
  };
  function renderValues() {
    values.replaceChildren();
    for(const code of selected) {
      const chip=document.createElement('span'); chip.className='chip';
      const name=document.createElement('span'); name.textContent=text(code); chip.append(name);
      const remove=document.createElement('button'); remove.type='button'; remove.textContent='×'; remove.setAttribute('aria-label',`移除${text(code)}`);
      remove.onclick=()=>{selected=selected.filter(item=>item!==code);emit();}; chip.append(remove); values.append(chip);
    }
    values.append(input); input.setAttribute('aria-label',config.label);
    input.placeholder=config.multiple?'输入代码或名称，回车添加':selected.length?'搜索其他股票':'输入代码或名称';
    count.textContent=config.multiple?`已选择 ${selected.length}/10 只 · 至少2只才可加载`:'可输入新代码，回车确认';
  }
  function renderList() {
    const needle=query.trim().toLowerCase();
    filtered=config.options.filter(item=>!needle||`${item.code} ${item.name}`.toLowerCase().includes(needle)).slice(0,80);
    list.replaceChildren();
    filtered.forEach((item,index)=>{
      const option=document.createElement('button'); option.type='button'; option.className='option'+(index===focused?' focused':'');
      option.setAttribute('role','option'); option.setAttribute('aria-selected',String(selected.includes(item.code)));
      const check=document.createElement('span'); check.className='check'; check.textContent=selected.includes(item.code)?'✓':item.watched?'★':'';
      const name=document.createElement('span'); name.textContent=text(item.code); option.append(check,name);
      option.onmousedown=event=>event.preventDefault(); option.onclick=()=>choose(item.code); list.append(option);
    });
    if(filtered.length===0||filtered.length===80) {
      const message=document.createElement('div'); message.className='message';
      message.textContent=filtered.length?'输入名称或代码缩小候选范围':'没有目录候选；可输入代码并按回车确认'; list.append(message);
    }
  }
  arrow.onmousedown=event=>event.preventDefault(); arrow.onclick=()=>setOpen(!opened);
  input.onfocus=()=>{};
  input.oninput=()=>{query=input.value;focused=-1;setOpen(true);};
  input.onclick=()=>setOpen(true);
  input.onkeydown=event=>{
    if(event.isComposing) return;
    if(event.key==='Escape'&&opened){event.preventDefault();event.stopPropagation();setOpen(false);return;}
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault();setOpen(true);focused=Math.max(0,Math.min(filtered.length-1,focused+(event.key==='ArrowDown'?1:-1)));renderList();
      list.querySelector('.focused')?.scrollIntoView({block:'nearest'});return;
    }
    if(event.key==='Enter'){
      event.preventDefault();
      const raw=input.value.trim();
      if(focused>=0&&filtered[focused]){choose(filtered[focused].code);return;}
      const exact=config.options.find(item=>item.code===raw||item.name===raw);
      if(exact){choose(exact.code);return;}
      if(raw&&(config.market==='美股'||/[0-9]/.test(raw))){
        const additions=raw.split(/[,，;；\s]+/).filter(Boolean).map(code=>code.split(/[（(]/)[0]);
        const next=config.multiple?[...new Set([...selected,...additions])]:additions.slice(0,1);
        if(next.length>10){count.textContent='最多选择10只股票，请先移除部分股票';return;}
        selected=next;
        query='';input.value='';emit();if(!config.multiple)setOpen(false);
      } else if(filtered.length===1) choose(filtered[0].code);
    }
  };
  const outside=event=>{if(!event.composedPath().includes(root))setOpen(false);};
  document.addEventListener('pointerdown',outside);
  root._picker={update(next){config=next;labels=new Map(config.options.map(item=>[item.code,item.name]));selected=[...next.selected];label.textContent=next.label;renderValues();if(opened)renderList();}};
  root._picker.update(data);
  input.value=query;setOpen(opened);
  return ()=>{root._pickerUi={opened,query};document.removeEventListener('pointerdown',outside);delete root._picker;};
}
"""


def _component():
    # Registries belong to the current runtime; a process-global cached callable
    # can outlive its registry after a runtime restart (including AppTest).
    return st.components.v2.component("quantlab_security_picker", html='<div class="ql-security-picker"></div>', css=CSS, js=JS)


def commit_selection(market, target, multiple, selection):
    """Validate client values before replacing the last valid selection."""
    if not isinstance(selection, list) or any(not isinstance(value, str) for value in selection):
        raise ValueError("股票选择数据无效。")
    codes = _selection(market, "", selection)
    if not multiple and len(codes) > 1:
        raise ValueError("单股研究只能选择一只股票。")
    return ",".join(codes) if multiple else next(iter(codes), "")


def _selection(market, text, additions=()):
    if market != "美股":
        return comparison_selection(market, text, additions)
    from quant_lab.us_market import normalize_us_symbol
    codes = tuple(dict.fromkeys(normalize_us_symbol(code) for code in
        [*text.replace("，", ",").split(","), *additions] if code.strip()))
    if len(codes) > 10:
        raise ValueError("最多选择10只同市场股票，请先移除部分股票。")
    return codes


def render_security_picker(market, target, *, multiple=False, label="股票（代码 / 名称）"):
    labels = {}
    try:
        if market != "美股":
            directory = security_directory(market)
            labels = dict(directory.rows)
            if directory.error:
                st.warning(directory.error)
    except (OSError, ValueError, KeyError, TypeError) as error:
        st.warning(str(error))
    try:
        watched = [code for item_market, code in list_watchlist() if item_market == market]
    except (OSError, ValueError, sqlite3.Error):
        watched = []
    current = st.session_state.get(target, "")
    try:
        selected = list(_selection(market, current))
    except ValueError:
        selected = []
    candidates = list(dict.fromkeys([*watched, *selected, *labels]))
    options = [{"code": code, "name": labels.get(code) or (names.cached_security_name(market, code) if market != "美股" else "") or "名称暂不可用", "watched": code in watched} for code in candidates]
    component_key = target + "_picker_" + market

    def changed():
        if multiple and st.session_state.get("compare_market") != market:
            return
        try:
            st.session_state[target] = commit_selection(market, target, multiple, st.session_state[component_key]["selection"])
            st.session_state.pop("_picker_error_" + target, None)
        except (ValueError, TypeError, KeyError) as error:
            st.session_state["_picker_error_" + target] = str(error)

    _component()(key=component_key, data={"market": market, "label": label, "multiple": multiple,
        "selected": selected, "options": options}, default={"selection": selected}, on_selection_change=changed)
    if st.session_state.get("_picker_error_" + target):
        st.warning(st.session_state["_picker_error_" + target])
    if market != "美股" and not labels and st.button("更新证券目录", key="picker_directory_" + market):
        from quant_lab.ui_jobs import submit_task
        submit_task("directory", market, security_directory, market, force=True)
    return st.session_state.get(target, "")
