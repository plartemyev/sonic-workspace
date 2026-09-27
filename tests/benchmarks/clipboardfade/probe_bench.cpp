// Benchmark runner for the clipboard fade campaign.
//
// Loads a QML scene (qrc: or local path), exposes bench.report()/quitApp()
// to QML (stderr is NOT suppressed, unlike the qml runtime tool), renders on
// the real display backend, and disables vsync for uncapped benchmarking
// unless QT_BENCH_KEEP_VSYNC=1.
#include <QGuiApplication>
#include <QQmlEngine>
#include <QQmlComponent>
#include <QQmlContext>
#include <QObject>
#include <QSurfaceFormat>
#include <QUrl>
#include <cstdio>

class BenchReporter : public QObject
{
    Q_OBJECT
public:
    using QObject::QObject;

    Q_INVOKABLE void report(const QString &msg)
    {
        fprintf(stderr, "BENCH %s\n", qPrintable(msg));
        fflush(stderr);
    }

    Q_INVOKABLE void quitApp()
    {
        QCoreApplication::exit(0);
    }
};
#include "probe_bench.moc"

int main(int argc, char **argv)
{
    if (!qEnvironmentVariableIsSet("QT_QPA_PLATFORM"))
        qputenv("QT_QPA_PLATFORM", "offscreen");
    if (!qEnvironmentVariableIsSet("QT_BENCH_KEEP_VSYNC")) {
        QSurfaceFormat fmt = QSurfaceFormat::defaultFormat();
        fmt.setSwapInterval(0);
        QSurfaceFormat::setDefaultFormat(fmt);
    }
    QGuiApplication app(argc, argv);
    if (argc < 2) {
        fprintf(stderr, "usage: clipfadebench <file.qml|qrc:...>\n");
        return 1;
    }
    const QString spec = QString::fromLocal8Bit(argv[1]);
    const QUrl url = spec.startsWith(u"qrc:") ? QUrl(spec) : QUrl::fromLocalFile(spec);

    QQmlEngine engine;
    BenchReporter bench;
    engine.rootContext()->setContextProperty("bench", &bench);

    QQmlComponent c(&engine, url);
    if (c.isError()) {
        const auto errs = c.errors();
        for (const QQmlError &e : errs)
            fprintf(stderr, "ERR: %s\n", qPrintable(e.toString()));
        return 2;
    }
    QObject *o = c.create();
    if (!o) {
        const auto errs = c.errors();
        for (const QQmlError &e : errs)
            fprintf(stderr, "ERR(create): %s\n", qPrintable(e.toString()));
        return 3;
    }
    fprintf(stderr, "BENCH started %s\n", qPrintable(spec));
    return app.exec();
}
