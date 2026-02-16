(function() {
  var trigger = document.getElementById('datePickerTrigger');
  var picker = document.getElementById('datePicker');
  if (!trigger || !picker) return;

  var isOpen = false;
  var availableSet = {};
  AVAILABLE_DATES.forEach(function(d) { availableSet[d] = true; });

  // 当前显示的月份
  var currentDate = new Date(CURRENT_DATE + 'T00:00:00');
  var viewYear = currentDate.getFullYear();
  var viewMonth = currentDate.getMonth();

  // 找可用日期的范围
  var sortedDates = AVAILABLE_DATES.slice().sort();
  var firstAvail = new Date(sortedDates[0] + 'T00:00:00');
  var lastAvail = new Date(sortedDates[sortedDates.length - 1] + 'T00:00:00');

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  function toDateStr(y, m, d) {
    return y + '-' + pad(m + 1) + '-' + pad(d);
  }

  function render() {
    var html = '';

    // 月份导航
    var canPrev = viewYear > firstAvail.getFullYear() || (viewYear === firstAvail.getFullYear() && viewMonth > firstAvail.getMonth());
    var canNext = viewYear < lastAvail.getFullYear() || (viewYear === lastAvail.getFullYear() && viewMonth < lastAvail.getMonth());

    var monthNames = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

    html += '<div class="dp-header">';
    html += '<button class="dp-nav' + (canPrev ? '' : ' dp-nav-disabled') + '" data-dir="-1">‹</button>';
    html += '<span class="dp-month">' + viewYear + ' 年 ' + monthNames[viewMonth] + '</span>';
    html += '<button class="dp-nav' + (canNext ? '' : ' dp-nav-disabled') + '" data-dir="1">›</button>';
    html += '</div>';

    // 星期头
    var days = ['一', '二', '三', '四', '五', '六', '日'];
    html += '<div class="dp-grid dp-weekdays">';
    days.forEach(function(d) {
      html += '<span class="dp-weekday">' + d + '</span>';
    });
    html += '</div>';

    // 日期网格
    var first = new Date(viewYear, viewMonth, 1);
    var startDay = (first.getDay() + 6) % 7; // 周一=0
    var daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

    html += '<div class="dp-grid dp-days">';

    // 前置空格
    for (var i = 0; i < startDay; i++) {
      html += '<span class="dp-day dp-empty"></span>';
    }

    for (var d = 1; d <= daysInMonth; d++) {
      var dateStr = toDateStr(viewYear, viewMonth, d);
      var hasContent = availableSet[dateStr];
      var isCurrent = dateStr === CURRENT_DATE;
      var isToday = dateStr === new Date().toISOString().slice(0, 10);

      var cls = 'dp-day';
      if (hasContent) cls += ' dp-has-content';
      if (isCurrent) cls += ' dp-current';
      if (isToday && !isCurrent) cls += ' dp-today';
      if (!hasContent) cls += ' dp-no-content';

      if (hasContent) {
        html += '<a href="' + dateStr + '.html" class="' + cls + '">' + d + '</a>';
      } else {
        html += '<span class="' + cls + '">' + d + '</span>';
      }
    }

    html += '</div>';

    picker.innerHTML = html;

    // 绑定月份导航
    picker.querySelectorAll('.dp-nav').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (this.classList.contains('dp-nav-disabled')) return;
        var dir = parseInt(this.getAttribute('data-dir'));
        viewMonth += dir;
        if (viewMonth < 0) { viewMonth = 11; viewYear--; }
        if (viewMonth > 11) { viewMonth = 0; viewYear++; }
        render();
      });
    });
  }

  function toggle() {
    isOpen = !isOpen;
    picker.classList.toggle('dp-open', isOpen);
    trigger.classList.toggle('dp-active', isOpen);
    if (isOpen) render();
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    picker.classList.remove('dp-open');
    trigger.classList.remove('dp-active');
  }

  trigger.addEventListener('click', function(e) {
    e.stopPropagation();
    toggle();
  });

  document.addEventListener('click', function(e) {
    if (!picker.contains(e.target) && e.target !== trigger) {
      close();
    }
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') close();
  });
})();
