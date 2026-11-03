'use strict';
try {
  Java.performNow(function () {
    const C = Java.use('android.app.MuMuImeBlackList');
    const Set = Java.use('java.util.Set');
    const JString = Java.use('java.lang.String');
    const original = {
      sImeClasses: 'com.ime.input.InputKb',
      sCertSha256: '9b200e7758e811605c957322c6865bb34989e79b363ad39895c7e4ef40976a96'
    };
    for (const key of Object.keys(original)) {
      const field = C.class.getDeclaredField(key);
      field.setAccessible(true);
      Java.cast(field.get(null), Set).add(JString.$new(original[key]));
    }
    console.log('MUMU_IME_RESTORED');
  });
} catch (e) {
  console.log('MUMU_IME_ERROR ' + e.stack);
}
