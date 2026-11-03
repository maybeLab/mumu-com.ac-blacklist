'use strict';
try {
  Java.performNow(function () {
    const C = Java.use('android.app.MuMuImeBlackList');
    const Set = Java.use('java.util.Set');
    const JString = Java.use('java.lang.String');
    const thread = Java.use('android.app.ActivityThread').currentActivityThread();
    const pm = thread.getSystemContext().getPackageManager();
    const info = pm.getPackageInfo.overload('java.lang.String', 'int').call(pm, 'com.ac', 64);
    const changes = [];
    function remove(fieldName, value) {
      const field = C.class.getDeclaredField(fieldName);
      field.setAccessible(true);
      const set = Java.cast(field.get(null), Set);
      const removed = set.remove(JString.$new(value));
      changes.push({field: fieldName, value: value, removed: removed});
    }
    remove('sImeClasses', 'com.ime.input.InputKb');
    const signatures = info.signatures.value;
    for (let i = 0; i < signatures.length; i++) {
      const digest = Java.use('java.security.MessageDigest').getInstance('SHA-256');
      const sha256 = String(C.toHex(digest.digest(signatures[i].toByteArray())));
      remove('sCertSha256', sha256);
    }
    const result = {pid: Process.id, changes: changes, blocked: C.isImeBlacklisted('com.ac/com.ime.input.InputKb')};
    console.log('MUMU_IME_FIXED ' + JSON.stringify(result));
  });
} catch (e) {
  console.log('MUMU_IME_ERROR ' + e.stack);
}
