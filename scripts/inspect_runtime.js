'use strict';
try {
  Java.performNow(function () {
    const C = Java.use('android.app.MuMuImeBlackList');
    const Set = Java.use('java.util.Set');
    const JString = Java.use('java.lang.String');
    const ArrayReflection = Java.use('java.lang.reflect.Array');
    function stringify(value) {
      return String(Java.cast(value, JString).toString());
    }
    const fields = C.class.getDeclaredFields();
    const result = {pid: Process.id, arrays: {}, sets: {}};
    for (let i = 0; i < fields.length; i++) {
      const field = fields[i];
      field.setAccessible(true);
      const name = String(field.getName());
      const type = String(field.getType().getName());
      const value = field.get(null);
      if (type === '[Ljava.lang.String;') {
        const items = [];
        for (let j = 0; j < ArrayReflection.getLength(value); j++) {
          items.push(stringify(ArrayReflection.get(value, j)));
        }
        result.arrays[name] = items;
      } else if (type === 'java.util.Set') {
        const set = Java.cast(value, Set);
        const items = set.toArray.overload().call(set);
        result.sets[name] = [];
        for (let j = 0; j < items.length; j++) result.sets[name].push(stringify(items[j]));
      }
    }
    const context = Java.use('android.app.ActivityThread').currentActivityThread().getSystemContext();
    const pm = context.getPackageManager();
    const info = pm.getPackageInfo.overload('java.lang.String', 'int').call(pm, 'com.ac', 64);
    result.packageCertificates = [];
    const signatures = info.signatures.value;
    for (let i = 0; i < signatures.length; i++) {
      const digest = Java.use('java.security.MessageDigest').getInstance('SHA-256');
      result.packageCertificates.push(String(C.toHex(digest.digest(signatures[i].toByteArray()))));
    }
    result.classBlocked = C.isImeBlacklisted('com.ac/com.ime.input.InputKb');
    result.certificateBlocked = result.packageCertificates.some(function (sha) {
      return result.sets.sCertSha256.indexOf(sha) !== -1;
    });
    console.log('MUMU_IME_INSPECT ' + JSON.stringify(result));
  });
} catch (e) {
  console.log('MUMU_IME_ERROR ' + e.stack);
}
