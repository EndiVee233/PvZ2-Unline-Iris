"""Build metadata and compile-only JVM declarations for recovered Java."""

import sys
from zipfile import ZipFile


RECOVERED_JAVA = {
    'AndroidUIEventManager': ('', '$UIEvent', '$UITouchTracker', '$UITouchEvent', '$UIKeyEvent',
                              '$UILongPressEvent', '$UIPinchEvent', '$UIFlickEvent',
                              '$UIBackButtonEvent', '$UITextInputEvent'),
    'AndroidSurfaceView': ('', '$1', '$AndroidEGLContextFactory', '$AndroidEGLConfigChooserInterface',
                           '$AndroidRenderer', '$GLWrapper'),
    'EditInputConnection': ('',),
    'GraphicsConfigChooser': ('',),
    'GLESRenderer': ('',),
    'GLES11Renderer': ('',),
    'GLES20Renderer': ('',),
    'SexyAppFrameworkActivity': ('', '$1', '$SplashImageComparator'),
    'AndroidSplashScreen': ('', '$AndroidSplashSurface', '$SplashImage'),
    'AndroidAssetUtils': ('',),
}
ROUND_THREE = {'SexyAppFrameworkActivity', 'AndroidSplashScreen', 'AndroidAssetUtils'}
FRAMEWORK = 'Lcom/popcap/SexyAppFramework/'


def recovered_descriptors(families):
    return {FRAMEWORK + name + suffix + ';' for name in families for suffix in RECOVERED_JAVA[name]}


def baseline_classpath(source, aster, output):
    sys.path.insert(0, str(aster.resolve() / 'src/recovered/tools'))
    try:
        from build_dex_reference_jar import Dex, make_class
    finally:
        sys.path.pop(0)

    with ZipFile(source) as apk:
        definitions = {definition['name']: definition for definition in Dex(apk.read('classes.dex')).classes()}

    nested_classes = {}
    for name, definition in definitions.items():
        annotations = definition['annotations']
        inner = annotations.get('Ldalvik/annotation/InnerClass;')
        outer = annotations.get('Ldalvik/annotation/EnclosingClass;', {}).get('value')
        if inner is not None and outer is not None:
            entry = (name, outer, inner.get('name'), inner['accessFlags'])
            nested_classes.setdefault(name, []).append(entry)
            nested_classes.setdefault(outer, []).append(entry)

    with ZipFile(output, 'w') as archive:
        archive.writestr('META-INF/COMPILE-ONLY.txt', 'Declarations for javac. Never package this JAR.')
        recovered = recovered_descriptors(RECOVERED_JAVA)
        for name, definition in definitions.items():
            if name not in recovered:
                archive.writestr(name[1:-1] + '.class', make_class(definition, nested_classes))
    return output
