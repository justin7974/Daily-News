(function() {
  var s = localStorage.getItem('theme');
  if (s) document.documentElement.setAttribute('data-theme', s);
  var btn = document.querySelector('.theme-toggle');
  if (btn) btn.addEventListener('click', function() {
    var cur = document.documentElement.getAttribute('data-theme');
    var dark = cur === 'dark' || (!cur && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var next = dark ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  });
})();
