'use strict';
async function startBoard(){
  const r=await fetch('/api/tasks/state',{cache:'no-store'});
  if(r.status===401)return;
  if(!r.ok)throw Error('Không thể tải dữ liệu máy chủ.');
  document.getElementById('loginStyle').remove();
  const css=document.createElement('link');css.rel='stylesheet';css.href='flowboard.css';document.head.append(css);
  document.body.innerHTML='<div id="app"><p style="padding:40px">Đang tải FlowBoard…</p></div><div id="serverTools"><span id="syncStatus">Đang kết nối…</span><button id="changePassword">Mật khẩu</button><button id="signOut">Đăng xuất</button></div>';
  document.getElementById('signOut').onclick=async()=>{if(window.gcmPending){alert('Dữ liệu chưa lưu xong. Vui lòng đợi hoặc xuất bản sao lưu.');return;}await fetch('/api/tasks/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});location.reload();};
  document.getElementById('changePassword').onclick=()=>{
    const d=document.createElement('dialog');d.innerHTML='<form><h3>Đổi mật khẩu</h3><p>Mật khẩu hiện tại</p><input name="old_password" type="password" autocomplete="current-password" required><p>Mật khẩu mới (tối thiểu 12 ký tự)</p><input name="new_password" type="password" autocomplete="new-password" minlength="12" maxlength="200" required><p class="error"></p><button type="button">Hủy</button> <button type="submit">Đổi mật khẩu</button></form>';document.body.append(d);d.querySelector('button').onclick=()=>d.remove();d.querySelector('form').onsubmit=async e=>{e.preventDefault();if(window.gcmPending){d.querySelector('.error').textContent='Chờ lưu xong dữ liệu trước khi đổi mật khẩu.';return;}const r=await fetch('/api/tasks/password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});const obj=await r.json();if(!r.ok){d.querySelector('.error').textContent=obj.error;return;}location.reload();};d.showModal();
  };
  const script=document.createElement('script');script.src='flowboard.js';document.body.append(script);
}
document.getElementById('loginForm').onsubmit=async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;const err=document.getElementById('loginError');err.textContent='';try{const r=await fetch('/api/tasks/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});const d=await r.json();if(!r.ok)throw Error(d.error);location.reload();}catch(ex){err.textContent=ex.message;}finally{button.disabled=false;}};
startBoard().catch(e=>document.getElementById('loginError').textContent=e.message);
