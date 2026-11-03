'use strict';
Java.perform(function () {
  Java.scheduleOnMainThread(function () {
    try {
      const Helper = Java.use('com.ime.input.a');
      const singleton = Helper.a.overload().call(Helper);
      Helper.a.overload('java.lang.String').call(singleton, 'MuMu输入法修复验证20261029');
      console.log('MUMU_IME_TEXT_SUBMITTED');
    } catch (e) {
      console.log('MUMU_IME_ERROR ' + e.stack);
    }
  });
});
