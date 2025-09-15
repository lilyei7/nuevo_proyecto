// Auth page scoped JS
(function(){
    function initAuth(){
        const root = document.querySelector('.auth-page');
        if(!root) return;

        // Password toggle inside auth forms
        const toggle = root.querySelector('.btn-password-toggle');
        const pwd = root.querySelector('input[type="password"]');
        if(toggle && pwd){
            toggle.addEventListener('click', ()=>{
                if(pwd.type === 'password') { pwd.type = 'text'; toggle.querySelector('i').classList.replace('bi-eye', 'bi-eye-slash'); }
                else { pwd.type = 'password'; toggle.querySelector('i').classList.replace('bi-eye-slash', 'bi-eye'); }
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAuth);
    } else {
        initAuth();
    }
})();
