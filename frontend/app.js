const $ = s => document.querySelector(s);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
async function api(path, options={}) {
  const response = await fetch(path, {credentials:"same-origin", ...options,
    headers:{"Content-Type":"application/json", ...(options.headers||{})}});
  const data = response.headers.get("content-type")?.includes("application/json") ? await response.json() : null;
  if (!response.ok) throw new Error(data?.detail || "Falha na solicitação");
  return data;
}
function table(target, headers, rows) {
  const container=$(target);
  if(!container) return;
  const head=headers.map(h=>"<th>"+esc(h)+"</th>").join("");
  const formatCell=v=>{const s=String(v??"");const m=s.match(/^(\\d{4})-(\\d{2})-(\\d{2})(?:T.*)?$/);return m?m[3]+"/"+m[2]+"/"+m[1]:s};
  const body=rows.map(r=>"<tr>"+r.map(v=>"<td>"+esc(formatCell(v))+"</td>").join("")+"</tr>").join("");
  container.innerHTML=rows.length ? "<table><thead><tr>"+head+"</tr></thead><tbody>"+body+"</tbody></table>" : '<div class="empty">Nenhum registro encontrado.</div>';
}
function fillSelect(selector, items, label, emptyLabel="Selecione") {
  const el=$(selector); if(!el) return;
  const old=el.value;
  el.innerHTML='<option value="">'+esc(emptyLabel)+'</option>'+items.map(x=>'<option value="'+esc(x.id)+'">'+esc(label(x))+'</option>').join("");
  if(old) el.value=old;
}
function fillDatalist(selector, values) {
  const el=$(selector); if(!el) return;
  el.innerHTML=[...new Set(values.filter(Boolean))].map(v=>'<option value="'+esc(v)+'"></option>').join("");
}
function setForm(form, values) {
  for(const field of form.elements) {
    if(!field.name || !(field.name in values)) continue;
    const value=values[field.name];
    field.value=value == null ? "" : String(value);
  }
}
function setHomePanel(){document.querySelectorAll(".tab,.panel").forEach(x=>x.classList.remove("active"));const homeTab=document.querySelector('.tab[data-panel="dashboard"]');if(homeTab)homeTab.classList.add("active");$("#dashboard")?.classList.add("active");}
function clearEmployeeForm() {
  $("#employee-form").reset(); $("#employee-id").value="";
  $("#employee-save").textContent="Cadastrar funcionário";
  $("#employee-cancel-edit")?.classList.add("hidden");
}
async function boot() {
  const unit=await api("/api/unit");
  const unitPanel=$("#unit-setup-panel");
  const loginPanel=$("#login-panel");
  const appContent=$("#app-content");
  if(!unit.configured) {
    unitPanel?.classList.remove("hidden");
    loginPanel?.classList.add("hidden");
    appContent?.classList.add("hidden");
    $("#logout")?.classList.add("hidden");
    $("#status").textContent="Identifique esta unidade";
    return;
  }
  unitPanel?.classList.add("hidden");
  const state=await api("/api/auth/status");
  window.__username=state.username; window.__role=state.role;
  $("#login-panel").classList.toggle("hidden",state.authenticated);
  $("#app-content").classList.toggle("hidden",!state.authenticated);
  $("#logout").classList.toggle("hidden",!state.authenticated);
  $("#status").textContent=unit.name+" • "+(state.authenticated ? "Conectado: "+state.username+" ("+state.role+")" : "Acesso restrito");
  
  document.querySelectorAll(".admin-only").forEach(el=>el.classList.toggle("hidden",state.role!=="admin"));
  if(state.authenticated) { setHomePanel(); await refresh(); }
}
async function refresh() {
 try {
  const [employees,types,grants,balances,history,limits,lookups]=await Promise.all([
   api("/api/employees"),api("/api/leave-types"),api("/api/grants"),api("/api/balances"),
   api("/api/history"+(()=>{const f=Object.fromEntries(new FormData($("#history-filter")).entries());const q=new URLSearchParams(Object.entries(f).filter(([k,v])=>v));return q.toString()?"?"+q.toString():""})()),
   api("/api/limits"),api("/api/lookups")]);
  window.__employees=employees;
  table("#type-list",["ID","Tipo","Validade (dias)","Descrição"],types.map(t=>[t.id,t.name,t.days_validity,t.description||"—"]));
  const employeeSearch=$("#employee-search")?.value.trim().toLocaleLowerCase("pt-BR")||"";
  const employeeOptions=employees.filter(e=>!employeeSearch||e.name.toLocaleLowerCase("pt-BR").includes(employeeSearch)||String(e.registration||"").toLocaleLowerCase("pt-BR").includes(employeeSearch));
  const employeeSelect=$("#employee-select");if(employeeSelect){const previous=employeeSelect.value;employeeSelect.innerHTML='<option value="">Selecione um funcionário</option>'+employeeOptions.map(e=>'<option value="'+esc(e.id)+'">'+esc(e.name+(e.registration?" — "+e.registration:""))+'</option>').join("");if(employeeOptions.some(e=>String(e.id)===previous))employeeSelect.value=previous;$("#employee-edit-selected").disabled=!employeeSelect.value||window.__role!=="admin";}
  window.__grants=grants;
  table("#grant-list",["Funcionário","Tipo","Evento","Validade","Total","Disponível","Adicionado por","Status","Ações"],grants.map(g=>[g.employee,g.leave_type,g.event_date,g.valid_until,Number(g.total_amount),Number(g.available_amount),g.created_by||"—",g.expired?"Expirada":"Válida",window.__role==="admin"?"Gerenciar":"—"]));
  $("#grant-list")?.querySelectorAll("tbody tr").forEach((tr,i)=>{const grant=grants[i];if(!grant)return;const td=tr.lastElementChild;td.textContent="";if(window.__role==="admin"){const edit=document.createElement("button");edit.className="secondary";edit.textContent="Editar";edit.addEventListener("click",()=>loadGrant(grant.id));const del=document.createElement("button");del.className="secondary";del.textContent="Excluir";del.style.marginLeft="6px";del.addEventListener("click",async()=>{if(!confirm("Excluir este folga? Folgas com histórico não podem ser excluídos."))return;try{await api("/api/grants/"+grant.id,{method:"DELETE"});await refresh()}catch(e){alert(e.message)}});td.append(edit,del)}else td.textContent="—";});
  table("#balances",["Funcionário","Categoria","Tipo","Data do evento","Validade","Saldo"],balances.map(b=>[b.employee,b.category||"—",b.leave_type,b.event_date,b.valid_until,Number(b.balance).toLocaleString("pt-BR",{maximumFractionDigits:2})]));
  table("#history-list",["Data de gozo","Funcionário","Categoria","Tipo","Quantidade","Turno","Registrado por","Ação"],history.map(h=>[h.leave_date,h.employee,h.category||"—",h.leave_type,h.quantity,h.shift,h.created_by,window.__role==="admin"?"Cancelar":"—"]));
  $("#history-list")?.querySelectorAll("tbody tr").forEach((tr,i)=>{const item=history[i];if(!item)return;const td=tr.lastElementChild;td.textContent="";if(window.__role==="admin"){const b=document.createElement("button");b.className="secondary";b.textContent="Cancelar";b.addEventListener("click",async()=>{if(confirm("Cancelar este gozo e devolver a quantidade ao saldo?")){try{await api("/api/history/"+item.id,{method:"DELETE"});await refresh()}catch(e){alert(e.message)}}});td.appendChild(b)}else td.textContent="—";});
  table("#limit-list",["Categoria","Limite diário"],limits.map(l=>[l.category,l.daily_limit==null?"Sem limite":l.daily_limit]));
  table("#expired-list",["Funcionário","Tipo de folga","Data do evento","Validade","Quantidade original","Saldo restante"],grants.filter(g=>g.expired).map(g=>[g.employee,g.leave_type,g.event_date,g.valid_until,g.total_amount,g.available_amount]));
  const selectedEmployee=Number($("#leave-employee-filter")?.value||0);
  const employeeGrants=selectedEmployee?grants.filter(g=>g.employee_id===selectedEmployee):[];
  if($("#employee-grants-table")) table("#employee-grants-table",["Descrição","Data do evento","Validade","Total","Disponível","Adicionado por","Ação"],employeeGrants.map(g=>[g.description||g.leave_type,g.event_date,g.valid_until,Number(g.total_amount),Number(g.available_amount),g.created_by||"—",window.__role==="admin"?"Gerenciar":"—"]));
  if($("#employee-grants-table")) $("#employee-grants-table")?.querySelectorAll("tbody tr").forEach((tr,i)=>{const g=employeeGrants[i];if(!g)return;const td=tr.lastElementChild;td.textContent="";if(window.__role==="admin"){const b=document.createElement("button");b.className="secondary";b.textContent="Editar";b.addEventListener("click",()=>loadGrant(g.id));const del=document.createElement("button");del.className="secondary danger-button";del.textContent="Excluir";del.style.marginLeft="6px";del.addEventListener("click",async()=>{if(!confirm("Excluir esta folga e devolver o saldo ao gerenciamento?"))return;try{await api("/api/grants/"+g.id,{method:"DELETE"});await refresh()}catch(e){alert(e.message)}});td.append(b,del)}});
  const employeeHistory=selectedEmployee?history.filter(h=>h.employee_id===selectedEmployee):[];
  if($("#employee-requests-table"))table("#employee-requests-table",["Data da solicitação","Descrição","Data do evento","Data do usufruto","Adicionado por"],employeeHistory.map(h=>[h.requested_at,h.leave_type,h.event_date||"—",h.leave_date,h.created_by]));
  if($("#employee-expired-table"))table("#employee-expired-table",["Descrição","Data do evento","Data de validade","Quantidade"],employeeGrants.filter(g=>g.expired).map(g=>[g.description||g.leave_type,g.event_date,g.valid_until,g.available_amount]));
  if($("#available-table"))table("#available-table",["Nome","Categoria","Quantidade de folgas"],balances.map(b=>[b.employee,b.leave_type,Number(b.balance).toLocaleString("pt-BR")]));
  const now=new Date();const today=[now.getFullYear(),String(now.getMonth()+1).padStart(2,"0"),String(now.getDate()).padStart(2,"0")].join("-");
  const todays=history.filter(h=>h.leave_date===today);
  if($("#today-leaves"))$("#today-leaves").innerHTML=todays.length?todays.map(x=>'<article class="person-row"><span class="person-avatar">'+esc((x.employee||"?").trim().charAt(0).toUpperCase())+'</span><div><strong>'+esc(x.employee)+'</strong><small>'+esc(x.category||"Equipe")+' · '+esc(x.shift||"Folga")+'</small></div><span class="person-tag">De folga</span></article>').join(""):'<div class="dashboard-empty"><span>✓</span><strong>Nenhuma folga programada para hoje</strong><p>Todos os funcionários estão disponíveis.</p></div>';
  const birthdays=employees.filter(e=>e.active&&e.birth_date&&e.birth_date.slice(5)===today.slice(5)).sort((a,b)=>a.name.localeCompare(b.name,"pt-BR"));
  if($("#today-birthdays"))$("#today-birthdays").innerHTML=birthdays.length?birthdays.map(x=>'<article class="person-row birthday-row"><span class="person-avatar birthday-avatar">🎉</span><div><strong>'+esc(x.name)+'</strong><small>'+esc(x.category||"Nossa equipe")+'</small><p class="birthday-message">🎂 Parabéns pelo seu dia! Que seu novo ciclo seja repleto de saúde, alegria e conquistas!</p></div></article>').join(""):'<div class="dashboard-empty"><span>🎂</span><strong>Nenhum aniversariante hoje</strong><p>Quando houver aniversário, a comemoração aparecerá aqui.</p></div>';
  fillSelect("#leave-employee-filter",employees.filter(e=>e.active),e=>e.name,"Selecione funcionário");

  fillSelect("#bank-employee",employees.filter(e=>e.active),e=>e.name);
  fillSelect("#grant-type",types.filter(t=>t.active),t=>t.name+" — "+t.days_validity+" dias");
  fillSelect("#use-grant",grants.filter(g=>!g.expired&&Number(g.available_amount)>0),g=>g.employee+" | "+g.leave_type+" | saldo "+g.available_amount+" | vence "+g.valid_until);
  fillDatalist("#cbo-codes",lookups.cbos.map(x=>x.code));
  fillDatalist("#unit-codes",lookups.units.map(x=>x.cnes));
  fillDatalist("#team-codes",lookups.teams.map(x=>x.ine));
  fillDatalist("#council-codes",lookups.councils.map(x=>x.sigla));
  fillDatalist("#state-codes",lookups.states.map(x=>x.uf));
  fillDatalist("#agency-codes",lookups.agencies.map(x=>x.sigla));
  fillDatalist("#municipality-codes",lookups.municipalities.map(x=>x.code));
  fillDatalist("#category-codes",lookups.cbos.map(x=>x.category));
  fillDatalist("#history-category-codes",lookups.cbos.map(x=>x.category).concat(employees.map(x=>x.category)));
  if(window.__role==="admin") {
    const [users,audit]=await Promise.all([api("/api/users"),api("/api/audit")]);
    table("#user-list",["ID","Usuário","Perfil","Ativo","Criado em","Ações"],users.map(u=>[u.id,u.username,u.role,u.active?"Sim":"Não",u.created_at,"Gerenciar"]));
    $("#user-list")?.querySelectorAll("tbody tr").forEach((tr,i)=>{
      const user=users[i]; if(!user)return;const td=tr.lastElementChild;td.textContent="";
      const toggle=document.createElement("button");toggle.className="secondary";toggle.textContent=user.active?"Desativar":"Ativar";
      toggle.disabled=user.username===window.__username;
      toggle.addEventListener("click",async()=>{if(!confirm((user.active?"Desativar":"Ativar")+" usuário "+user.username+"?"))return;try{await api("/api/users/"+user.id,{method:"PATCH",body:JSON.stringify({active:!user.active})});await refresh()}catch(e){alert(e.message)}});
      const reset=document.createElement("button");reset.className="secondary";reset.textContent="Nova senha";reset.style.marginLeft="6px";
      reset.addEventListener("click",async()=>{const password=prompt("Digite a nova senha (mínimo 12 caracteres):");if(password===null)return;if(password.length<12){alert("A senha precisa ter pelo menos 12 caracteres.");return}try{await api("/api/users/"+user.id,{method:"PATCH",body:JSON.stringify({password})});alert("Senha redefinida.")}catch(e){alert(e.message)}});
      const delUser=document.createElement("button");delUser.className="secondary danger-button";delUser.textContent="Excluir";delUser.style.marginLeft="6px";delUser.disabled=user.username===window.__username;delUser.addEventListener("click",async()=>{if(!confirm("Excluir definitivamente o usuário "+user.username+"?"))return;try{await api("/api/users/"+user.id,{method:"DELETE"});await refresh()}catch(e){alert(e.message)}});td.append(toggle,reset,delUser);
    });
    table("#audit-list",["Data","Usuário","Ação","Entidade","ID","Detalhe"],audit.map(a=>[a.created_at,a.username,a.action,a.entity,a.entity_id??"—",a.detail||"—"]));
  }
  $("#status").textContent="Conectado: "+window.__username+" ("+window.__role+")";
 } catch(e) { $("#status").textContent="Falha ao carregar: "+(e.message||"verifique o servidor"); console.error("Falha ao atualizar MARKYS:",e); }
}
async function loadEmployee(id) {
 try {
  const values=await api("/api/employees/"+id);setForm($("#employee-form"),values);$("#employee-id").value=id;
  $("#employee-save").textContent="Salvar alterações";$("#employee-cancel-edit")?.classList.remove("hidden");$("#employee-form").scrollIntoView({behavior:"smooth",block:"start"});
 } catch(e){alert(e.message)}
}
async function loadGrant(id) {
 const grant=(window.__grants||[]).find(g=>g.id===id);if(!grant)return;
 $("#leave-employee-filter").value=String(grant.employee_id);
 document.querySelector('[data-panel="leave-center"]').click();document.querySelector('[data-leave-view="manage"]').click();$("#grant-form").classList.remove("hidden");
 setForm($("#grant-form"),{id:grant.id,employee_id:grant.employee_id,leave_type_id:grant.leave_type_id,
   event_date:grant.event_date,quantity:grant.total_amount,description:grant.description||""});
 $("#grant-id").value=grant.id;$("#grant-save").textContent="Salvar folga";$("#grant-cancel-edit").classList.remove("hidden");
 $("#grant-form").scrollIntoView({behavior:"smooth",block:"start"});
}
function clearGrantForm(){ $("#grant-form").reset();$("#grant-id").value="";$("#grant-save").textContent="Adicionar";$("#grant-cancel-edit").classList.add("hidden");}
function submit(form,path,map,done=refresh) {
 $(form).addEventListener("submit",async ev=>{ev.preventDefault();const formElement=ev.currentTarget;const raw=Object.fromEntries(new FormData(formElement).entries());try{await api(path,{method:"POST",body:JSON.stringify(map(raw))});formElement.reset();await done();alert("Operação concluída.")}catch(e){alert(e.message)}});
}
$("#employee-cancel-edit")?.addEventListener("click",clearEmployeeForm);
$("#employee-search")?.addEventListener("input",()=>{const q=$("#employee-search").value.trim().toLocaleLowerCase("pt-BR");const list=(window.__employees||[]).filter(e=>!q||e.name.toLocaleLowerCase("pt-BR").includes(q)||String(e.registration||"").toLocaleLowerCase("pt-BR").includes(q));const select=$("#employee-select");if(select){const current=select.value;select.innerHTML='<option value="">Selecione um funcionário</option>'+list.map(e=>'<option value="'+esc(e.id)+'">'+esc(e.name+(e.registration?" — "+e.registration:""))+'</option>').join("");if(list.some(e=>String(e.id)===current))select.value=current;$("#employee-edit-selected").disabled=!select.value||window.__role!=="admin";}});
$("#employee-select")?.addEventListener("change",()=>{$("#employee-edit-selected").disabled=!$("#employee-select").value||window.__role!=="admin";});
$("#employee-edit-selected")?.addEventListener("click",()=>{const id=Number($("#employee-select").value);if(id)loadEmployee(id);});
$("#employee-form").addEventListener("submit",async ev=>{
 ev.preventDefault();if(window.__role!=="admin")return;
 const raw=Object.fromEntries(new FormData(ev.currentTarget).entries());const id=raw.id;delete raw.id;
 const data={...raw};
 for(const k of ["contract_id","sector_id"])data[k]=data[k]?Number(data[k]):null;
 for(const k of Object.keys(data))if(data[k]==="")data[k]=null;
 data.name=raw.name;
 try{await api(id?"/api/employees/"+id:"/api/employees",{method:id?"PUT":"POST",body:JSON.stringify(data)});clearEmployeeForm();await refresh();alert("Funcionário salvo com sucesso.")}catch(e){alert(e.message)}
});


submit("#type-form","/api/leave-types",v=>({name:v.name,description:v.description||null,days_validity:Number(v.days_validity)}));
$("#grant-form").addEventListener("submit",async ev=>{
 ev.preventDefault();if(window.__role!=="admin")return;
 const raw=Object.fromEntries(new FormData(ev.currentTarget).entries());const id=raw.id;delete raw.id;
 const payload={...raw,employee_id:Number($("#leave-employee-filter").value),leave_type_id:Number(raw.leave_type_id),quantity:Number(raw.quantity),description:raw.description||null};
 try{await api(id?"/api/grants/"+id:"/api/grants",{method:id?"PUT":"POST",body:JSON.stringify(payload)});clearGrantForm();await refresh();alert("Folga salva com sucesso.")}catch(e){alert(e.message)}
});
$("#grant-cancel-edit").addEventListener("click",()=>{$("#grant-form").classList.add("hidden");clearGrantForm()});
$("#leave-employee-filter").addEventListener("change",()=>refresh());
$("#leave-employee-search").addEventListener("input",ev=>{const q=ev.currentTarget.value.trim().toLocaleLowerCase("pt-BR");const items=(window.__employees||[]).filter(e=>e.active&&e.name.toLocaleLowerCase("pt-BR").includes(q));fillSelect("#leave-employee-filter",items,e=>e.name,"Selecione funcionário");if(items.length===1)$("#leave-employee-filter").value=String(items[0].id);});
$("#leave-employee-search").addEventListener("focus",()=>{const q=$("#leave-employee-search").value.trim().toLocaleLowerCase("pt-BR");const items=(window.__employees||[]).filter(e=>e.active&&e.name.toLocaleLowerCase("pt-BR").includes(q));fillSelect("#leave-employee-filter",items,e=>e.name,"Selecione funcionário");});
document.querySelectorAll(".leave-view").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll(".leave-view").forEach(x=>x.classList.toggle("active",x===b));document.querySelectorAll(".leave-view-panel").forEach(x=>x.classList.toggle("active",x.id==="leave-view-"+b.dataset.leaveView));}));
$("#new-grant-open").addEventListener("click",()=>{if(!$("#leave-employee-filter").value){alert("Selecione um funcionário primeiro.");return;}clearGrantForm();$("#grant-form").classList.remove("hidden");$("#grant-form").scrollIntoView({behavior:"smooth",block:"nearest"});});
$("#grant-cancel-edit").addEventListener("click",()=>{$("#grant-form").classList.add("hidden");clearGrantForm()});
$("#new-request-open").addEventListener("click",()=>{const sel=$("#request-grant");sel.innerHTML='<option value="">Selecione uma folga disponível</option>'+((window.__grants||[]).filter(g=>g.employee_id===Number($("#leave-employee-filter").value)&&!g.expired&&Number(g.available_amount)>0).map(g=>'<option value="'+g.id+'">'+esc(g.description||g.leave_type)+' — saldo '+g.available_amount+'</option>').join(""));$("#request-date").value=new Date().toISOString().slice(0,10);$("#request-form").classList.remove("hidden")});
$("#request-cancel").addEventListener("click",()=>{$("#request-form").reset();$("#request-form").classList.add("hidden")});
$("#request-grant").addEventListener("change",()=>{const g=(window.__grants||[]).find(x=>x.id===Number($("#request-grant").value));$("#request-event-date").value=g?.event_date||"";$("#request-valid-until").value=g?.valid_until||"";});
$("#request-form").addEventListener("submit",async ev=>{ev.preventDefault();if(window.__role!=="admin")return;const v=Object.fromEntries(new FormData(ev.currentTarget).entries());try{await api("/api/history",{method:"POST",body:JSON.stringify({grant_id:Number(v.grant_id),leave_date:v.leave_date,requested_at:v.requested_at,quantity:Number(v.quantity),shift:v.shift})});$("#request-form").reset();$("#request-form").classList.add("hidden");await refresh();alert("Solicitação registrada com sucesso.")}catch(e){alert(e.message)}});


$("#history-filter").addEventListener("submit",ev=>{ev.preventDefault();refresh()});
$("#history-clear").addEventListener("click",()=>{$("#history-filter").reset();refresh()});
submit("#use-form","/api/history",v=>({...v,grant_id:Number(v.grant_id),quantity:Number(v.quantity)}));
submit("#limit-form","/api/limits",v=>({...v,daily_limit:v.daily_limit===""?null:Number(v.daily_limit)}));
submit("#user-form","/api/users",v=>({username:v.username,password:v.password,role:v.role}),async()=>{await refresh()});
const rememberedLogin=localStorage.getItem("markys_remembered_login")||"";
$("#login-cpf").value=rememberedLogin;
$("#remember-login").checked=Boolean(rememberedLogin);
$("#unit-setup-form").addEventListener("submit",async ev=>{
  ev.preventDefault();
  const form=ev.currentTarget;
  const name=String(new FormData(form).get("name")||"").trim();
  try {
    await api("/api/unit",{method:"POST",body:JSON.stringify({name})});
    await boot();
  } catch(e) { $("#unit-setup-error").textContent=e.message; }
});
$("#login-form").addEventListener("submit",async ev=>{ev.preventDefault();const formElement=ev.currentTarget;$("#login-error").className="error";$("#login-error").style.color="";const v=Object.fromEntries(new FormData(formElement).entries());v.username=$("#login-cpf").value.trim();try{await api("/api/auth/login",{method:"POST",body:JSON.stringify(v)});if($("#remember-login").checked)localStorage.setItem("markys_remembered_login",v.username);else localStorage.removeItem("markys_remembered_login");formElement.reset();await boot()}catch(e){$("#login-error").textContent=e.message}});
$("#forgot-password-link").addEventListener("click",ev=>{ev.preventDefault();$("#forgot-password-help").classList.toggle("hidden");});
$("#register-link").addEventListener("click",ev=>{ev.preventDefault();$("#registration-area").classList.toggle("hidden");if(!$("#registration-area").classList.contains("hidden"))$("#registration-area").scrollIntoView({behavior:"smooth",block:"nearest"});});
$("#registration-form").addEventListener("submit",async ev=>{ev.preventDefault();const v=Object.fromEntries(new FormData(ev.currentTarget).entries());const cpf=v.cpf.replace(/\D/g,"");if(v.password!==v.confirm_password){$("#registration-error").textContent="As senhas não conferem.";return;}try{await api("/api/auth/register",{method:"POST",body:JSON.stringify({cpf,password:v.password,confirm_password:v.confirm_password})});$("#login-cpf").value=cpf;$("#registration-form").reset();$("#registration-area").classList.add("hidden");$("#login-error").textContent="Cadastro realizado. Entre com seu CPF e senha.";$("#login-error").classList.remove("error");$("#login-error").style.color="#176b42";}catch(e){$("#registration-error").textContent=e.message;}});
$("#admin-password-form").addEventListener("submit",async ev=>{ev.preventDefault();const formElement=ev.currentTarget;const v=Object.fromEntries(new FormData(formElement).entries());if(v.new_password!==v.confirm_password){$("#password-change-message").textContent="A confirmação da nova senha não confere." ;$("#password-change-message").classList.remove("hidden");return;}try{await api("/api/auth/change-password",{method:"POST",body:JSON.stringify({current_password:v.current_password,new_password:v.new_password,confirm_password:v.confirm_password})});formElement.reset();$("#password-change-message").textContent="Senha administrativa alterada com sucesso." ;$("#password-change-message").classList.remove("hidden");}catch(e){$("#password-change-message").textContent=e.message;$("#password-change-message").classList.remove("hidden");}});
$("#logout").addEventListener("click",async()=>{try{await api("/api/auth/logout",{method:"POST"});}finally{window.__username=null;window.__role=null;$("#login-form").reset();$("#login-error").textContent="";$("#app-content").classList.add("hidden");$("#login-panel").classList.remove("hidden");$("#logout").classList.add("hidden");$("#status").textContent="Acesso restrito";document.querySelectorAll(".panel,.tab").forEach(x=>x.classList.remove("active"));$("#login-panel").classList.add("active");$("#login-cpf").focus();}});
document.querySelectorAll(".tab").forEach(b=>b.addEventListener("click",()=>{if(!$("#"+b.dataset.panel))return;document.querySelectorAll(".tab,.panel").forEach(x=>x.classList.remove("active"));b.classList.add("active");$("#"+b.dataset.panel).classList.add("active");if(b.dataset.panel==="leave-center"){if($("#leave-employee-filter"))$("#leave-employee-filter").value="";if($("#leave-employee-search"))$("#leave-employee-search").value="";document.querySelector('[data-leave-view="manage"]').click();refresh();}}));
$("#refresh").addEventListener("click",refresh);
$("#expired-refresh").addEventListener("click",refresh);

api("/api/auth/status").then(s=>{window.__username=s.username;window.__role=s.role;return boot()}).catch(e=>{$("#status").textContent="Servidor indisponível";console.error("MARKYS não conseguiu conectar:",e)});


// Padroniza campos de texto em maiúsculas sem alterar senhas nem o valor técnico de campos ocultos.
document.addEventListener("input",ev=>{const el=ev.target;if(!(el instanceof HTMLInputElement||el instanceof HTMLTextAreaElement))return;if(["password","hidden"].includes(el.type)||el.readOnly||el.disabled)return;const start=el.selectionStart,end=el.selectionEnd;const upper=el.value.toLocaleUpperCase("pt-BR");if(el.value!==upper){el.value=upper;try{el.setSelectionRange(start,end)}catch(_){}}});

