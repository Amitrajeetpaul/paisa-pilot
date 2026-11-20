package com.paisapilot.app;

import android.app.AppOpsManager;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.usage.UsageStats;
import android.app.usage.UsageStatsManager;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Process;
import android.provider.Settings;
import androidx.core.app.NotificationCompat;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.Calendar;
import java.util.List;
import org.json.JSONException;

/**
 * Reads how many days each app was opened, using Android's Usage Access permission.
 * The user grants it once in Settings; the data never leaves the phone except the
 * small "days opened" counts the app sends to work out savings.
 */
@CapacitorPlugin(name = "UsageAccess")
public class UsageAccessPlugin extends Plugin {
    private static final String CHANNEL_ID = "subscription_alerts";
    private static final long MIN_FOREGROUND_MS = 60_000L; // under a minute is not "using" an app

    private boolean hasAccess() {
        Context ctx = getContext();
        AppOpsManager ops = (AppOpsManager) ctx.getSystemService(Context.APP_OPS_SERVICE);
        int mode = ops.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), ctx.getPackageName());
        return mode == AppOpsManager.MODE_ALLOWED;
    }

    @PluginMethod
    public void hasAccess(PluginCall call) {
        JSObject ret = new JSObject();
        ret.put("granted", hasAccess());
        call.resolve(ret);
    }

    /** Opens Android's "Usage access" screen, where the user switches Paisa Pilot on. */
    @PluginMethod
    public void openSettings(PluginCall call) {
        Intent intent = new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        getContext().startActivity(intent);
        call.resolve();
    }

    /**
     * For each package, the calendar days (YYYY-MM-DD) in the last `days` days on which it was in
     * the foreground for at least a minute. Android only keeps about a week of daily detail, so the
     * web app saves what it sees and builds a longer history over time.
     */
    @PluginMethod
    public void getDaysUsed(PluginCall call) {
        if (!hasAccess()) {
            call.reject("Usage access is not allowed yet");
            return;
        }
        JSArray packages = call.getArray("packages");
        int days = call.getInt("days", 7);
        if (packages == null) {
            call.reject("packages is required");
            return;
        }
        UsageStatsManager usm = (UsageStatsManager) getContext().getSystemService(Context.USAGE_STATS_SERVICE);
        Calendar end = Calendar.getInstance();
        Calendar start = Calendar.getInstance();
        start.add(Calendar.DAY_OF_YEAR, -days);
        List<UsageStats> stats = usm.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, start.getTimeInMillis(), end.getTimeInMillis());

        JSObject result = new JSObject();
        try {
            for (int i = 0; i < packages.length(); i++) {
                String pkg = packages.getString(i);
                JSArray usedDays = new JSArray();
                if (stats != null) {
                    for (UsageStats s : stats) {
                        if (pkg.equals(s.getPackageName()) && s.getTotalTimeInForeground() >= MIN_FOREGROUND_MS) {
                            Calendar day = Calendar.getInstance();
                            day.setTimeInMillis(s.getFirstTimeStamp());
                            String key = String.format(java.util.Locale.US, "%04d-%02d-%02d",
                                    day.get(Calendar.YEAR), day.get(Calendar.MONTH) + 1, day.get(Calendar.DAY_OF_MONTH));
                            usedDays.put(key);
                        }
                    }
                }
                result.put(pkg, usedDays);
            }
        } catch (JSONException e) {
            call.reject("Could not read usage");
            return;
        }
        JSObject ret = new JSObject();
        ret.put("days", result);
        call.resolve(ret);
    }

    /** Shows a notification such as "You opened Netflix 1 day in 30. Pausing saves Rs 649." */
    @PluginMethod
    public void notify(PluginCall call) {
        String title = call.getString("title", "Paisa Pilot");
        String body = call.getString("body", "");
        int id = call.getInt("id", (int) (System.currentTimeMillis() % 100000));
        Context ctx = getContext();
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(new NotificationChannel(CHANNEL_ID, "Subscription alerts", NotificationManager.IMPORTANCE_DEFAULT));
        }
        if (Build.VERSION.SDK_INT >= 33 && ctx.checkSelfPermission("android.permission.POST_NOTIFICATIONS") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            getActivity().requestPermissions(new String[] {"android.permission.POST_NOTIFICATIONS"}, 4301);
            JSObject ret = new JSObject();
            ret.put("shown", false);
            ret.put("needsPermission", true);
            call.resolve(ret);
            return;
        }
        Intent open = ctx.getPackageManager().getLaunchIntentForPackage(ctx.getPackageName());
        PendingIntent pi = PendingIntent.getActivity(ctx, 0, open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        NotificationCompat.Builder b = new NotificationCompat.Builder(ctx, CHANNEL_ID)
                .setSmallIcon(ctx.getApplicationInfo().icon)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
                .setContentIntent(pi)
                .setAutoCancel(true);
        nm.notify(id, b.build());
        JSObject ret = new JSObject();
        ret.put("shown", true);
        call.resolve(ret);
    }
}
