package com.canpse.punho;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Tela única: endereço do PC, token, ligar/desligar. */
public class MainActivity extends Activity {
    static final String PADRAO_URL = "";  // ex.: http://192.168.0.10:8787 (IP do PC)

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, 1);
        }
        final SharedPreferences prefs = getSharedPreferences("punho", MODE_PRIVATE);

        LinearLayout tela = new LinearLayout(this);
        tela.setOrientation(LinearLayout.VERTICAL);
        int m = (int) (24 * getResources().getDisplayMetrics().density);
        tela.setPadding(m, m, m, m);

        TextView explica = new TextView(this);
        explica.setText("Punho v" + PunhoService.VERSAO + ": terminal do relógio.\n"
                + "Toda a lógica mora na central do PC.\n");
        tela.addView(explica);

        final EditText url = new EditText(this);
        url.setHint("http://IP-do-PC:8787");
        url.setText(prefs.getString("url", PADRAO_URL));
        url.setInputType(InputType.TYPE_TEXT_VARIATION_URI);
        tela.addView(url);

        final EditText token = new EditText(this);
        token.setHint("token");
        token.setText(prefs.getString("token", BuildToken.TOKEN));
        tela.addView(token);

        Button ligar = new Button(this);
        ligar.setText("Ligar");
        ligar.setOnClickListener(v -> {
            prefs.edit()
                    .putString("url", url.getText().toString().trim())
                    .putString("token", token.getText().toString().trim())
                    .apply();
            Intent i = new Intent(this, PunhoService.class);
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(i); else startService(i);
        });
        tela.addView(ligar);

        Button desligar = new Button(this);
        desligar.setText("Desligar");
        desligar.setOnClickListener(v -> stopService(new Intent(this, PunhoService.class)));
        tela.addView(desligar);

        setContentView(tela);
    }
}
