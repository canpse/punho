package com.canpse.punho;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;
import android.media.MediaMetadata;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Terminal burro: finge ser um player de música, repassa os três botões do relógio
 * pra central no PC e mostra a linha que ela mandar. Toda a lógica mora no PC.
 */
public class PunhoService extends Service {
    static final String VERSAO = "1.0";
    static final String CANAL_FIXO = "punho_fixo";
    static final String CANAL_AVISO = "punho_resultado";

    private MediaSession sessao;
    private final Handler principal = new Handler(Looper.getMainLooper());
    private final ExecutorService botoes = Executors.newSingleThreadExecutor();
    private Thread escuta;
    private volatile boolean vivo = true;

    private String linha = "Conectando…";
    private volatile int versao = 0;
    private volatile int ultimaNotif = -1; // -1: na primeira escuta não reapresenta avisos velhos
    private long ultimoBotao = 0;
    private String ultimoTipo = "";

    @Override
    public void onCreate() {
        super.onCreate();
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(
                CANAL_FIXO, "Punho ligado", NotificationManager.IMPORTANCE_LOW));
        nm.createNotificationChannel(new NotificationChannel(
                CANAL_AVISO, "Avisos do PC", NotificationManager.IMPORTANCE_DEFAULT));

        sessao = new MediaSession(this, "punho");
        sessao.setCallback(new MediaSession.Callback() {
            @Override public void onSkipToNext() { apertar("proxima"); }
            @Override public void onSkipToPrevious() { apertar("anterior"); }
            @Override public void onPlay() { apertar("play"); }
            @Override public void onPause() { apertar("play"); }
            @Override public void onStop() { apertar("play"); }
        });
        sessao.setPlaybackState(new PlaybackState.Builder()
                .setActions(PlaybackState.ACTION_PLAY | PlaybackState.ACTION_PAUSE
                        | PlaybackState.ACTION_PLAY_PAUSE | PlaybackState.ACTION_STOP
                        | PlaybackState.ACTION_SKIP_TO_NEXT | PlaybackState.ACTION_SKIP_TO_PREVIOUS)
                .setState(PlaybackState.STATE_PLAYING, 0, 1f)
                .build());
        sessao.setActive(true);

        Notification n = notificacaoFixa();
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
        } else {
            startForeground(1, n);
        }
        mostrar(linha);
        silencio();

        escuta = new Thread(this::escutar, "punho-escuta");
        escuta.start();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && intent.getAction() != null) {
            apertar(intent.getAction());
        } else {
            silencio();
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        vivo = false;
        if (escuta != null) escuta.interrupt();
        sessao.setActive(false);
        sessao.release();
        botoes.shutdownNow();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent i) { return null; }

    // ---------- botões -> PC ----------

    private void apertar(final String b) {
        long agora = SystemClock.elapsedRealtime();
        // o relógio às vezes manda o mesmo botão duplicado em seguida
        if (b.equals(ultimoTipo) && agora - ultimoBotao < 250) return;
        ultimoBotao = agora;
        ultimoTipo = b;
        botoes.execute(() -> {
            try {
                JSONObject r = new JSONObject(http("POST", "/botao?b=" + b, 8000));
                aplicar(r.optString("linha", linha), r.optInt("versao", versao));
            } catch (Exception e) {
                principal.post(() -> mostrar("PC fora do ar"));
            }
        });
        silencio();
    }

    // ---------- PC -> relógio (espera longa) ----------

    private void escutar() {
        while (vivo) {
            try {
                JSONObject r = new JSONObject(http("GET",
                        "/espera?versao=" + versao + "&notif=" + Math.max(ultimaNotif, 0), 40000));
                JSONArray ns = r.optJSONArray("notifs");
                if (ns != null) {
                    for (int i = 0; i < ns.length(); i++) {
                        JSONObject n = ns.getJSONObject(i);
                        int id = n.getInt("id");
                        if (ultimaNotif >= 0 && id > ultimaNotif) {
                            final String t = n.optString("titulo"), x = n.optString("texto");
                            principal.post(() -> avisar(t, x));
                        }
                        if (ultimaNotif < 0 || id > ultimaNotif) ultimaNotif = Math.max(ultimaNotif, id);
                    }
                }
                if (ultimaNotif < 0) ultimaNotif = 0;
                aplicar(r.optString("linha", linha), r.optInt("versao", versao));
            } catch (Exception e) {
                if (!vivo) return;
                principal.post(() -> mostrar("PC fora do ar"));
                try { Thread.sleep(5000); } catch (InterruptedException ie) { return; }
            }
        }
    }

    private void aplicar(final String l, final int v) {
        if (v < versao) return;
        versao = v;
        principal.post(() -> mostrar(l));
    }

    private String http(String metodo, String caminho, int leitura) throws Exception {
        SharedPreferences p = getSharedPreferences("punho", MODE_PRIVATE);
        URL url = new URL(p.getString("url", MainActivity.PADRAO_URL) + caminho);
        HttpURLConnection c = (HttpURLConnection) url.openConnection();
        c.setRequestMethod(metodo);
        c.setConnectTimeout(5000);
        c.setReadTimeout(leitura);
        c.setRequestProperty("X-Token", p.getString("token", BuildToken.TOKEN));
        if (metodo.equals("POST")) {
            c.setDoOutput(true);
            c.getOutputStream().close();
        }
        int codigo = c.getResponseCode();
        if (codigo != 200) throw new Exception("HTTP " + codigo);
        try (InputStream in = c.getInputStream()) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int lidos;
            while ((lidos = in.read(buf)) > 0) out.write(buf, 0, lidos);
            return out.toString("UTF-8");
        } finally {
            c.disconnect();
        }
    }

    // ---------- o que o relógio vê ----------

    private void mostrar(String l) {
        linha = l;
        sessao.setMetadata(new MediaMetadata.Builder()
                .putString(MediaMetadata.METADATA_KEY_TITLE, l)
                .putString(MediaMetadata.METADATA_KEY_ARTIST, "Punho v" + VERSAO)
                .build());
        getSystemService(NotificationManager.class).notify(1, notificacaoFixa());
    }

    private Notification notificacaoFixa() {
        return new Notification.Builder(this, CANAL_FIXO)
                .setSmallIcon(android.R.drawable.ic_media_play)
                .setContentTitle(linha)
                .setContentText("Punho v" + VERSAO)
                .setOngoing(true)
                .addAction(new Notification.Action.Builder(null, "⏮", intencao("anterior", 1)).build())
                .addAction(new Notification.Action.Builder(null, "⏯", intencao("play", 2)).build())
                .addAction(new Notification.Action.Builder(null, "⏭", intencao("proxima", 3)).build())
                .setStyle(new Notification.MediaStyle()
                        .setMediaSession(sessao.getSessionToken())
                        .setShowActionsInCompactView(0, 1, 2))
                .build();
    }

    private PendingIntent intencao(String acao, int codigo) {
        Intent i = new Intent(this, PunhoService.class).setAction(acao);
        return PendingIntent.getService(this, codigo, i, PendingIntent.FLAG_IMMUTABLE);
    }

    private int idAviso = 100;

    private void avisar(String titulo, String texto) {
        Notification n = new Notification.Builder(this, CANAL_AVISO)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(titulo)
                .setContentText(texto)
                .setStyle(new Notification.BigTextStyle().bigText(texto))
                .setAutoCancel(true)
                .build();
        NotificationManager nm = getSystemService(NotificationManager.class);
        idAviso = idAviso >= 105 ? 100 : idAviso + 1; // guarda os últimos 6
        nm.notify(idAviso, n);
    }

    /** Meio segundo de silêncio: o Android manda os botões de mídia pra quem tocou áudio por último. */
    private void silencio() {
        try {
            int taxa = 8000, amostras = taxa / 2;
            AudioTrack t = new AudioTrack.Builder()
                    .setAudioAttributes(new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                    .setAudioFormat(new AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(taxa)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build())
                    .setBufferSizeInBytes(amostras * 2)
                    .setTransferMode(AudioTrack.MODE_STATIC)
                    .build();
            t.write(new short[amostras], 0, amostras);
            t.play();
            principal.postDelayed(t::release, 1500);
        } catch (Exception ignorado) {
        }
    }
}
