import subprocess
import threading
import time
import json
import csv
import os
from datetime import datetime
from collections import deque
from flask import Flask, Response, jsonify

app = Flask(__name__)

# Per-server stats
stats = {
    "web1": {"count": 0, "last": "—"},
    "web2": {"count": 0, "last": "—"},
    "web3": {"count": 0, "last": "—"},
}

# Time-series: store up to 60 snapshots
time_series = deque(maxlen=60)
lock = threading.Lock()


# ── Background: stream docker logs ─────────────────────────────────────────────
def stream_logs(container: str):
    try:
        proc = subprocess.Popen(
            ["docker", "logs", "-f", "--tail", "0", container],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in proc.stdout:
            if "Traffic received on" in line:
                with lock:
                    stats[container]["count"] += 1
                    stats[container]["last"] = datetime.now().strftime("%H:%M:%S")
    except Exception as e:
        print(f"[{container}] Log stream error: {e}")


def record_timeseries():
    while True:
        time.sleep(2)
        with lock:
            point = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "web1": stats["web1"]["count"],
                "web2": stats["web2"]["count"],
                "web3": stats["web3"]["count"],
            }
        time_series.append(point)


# ── Routes ──────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return HTML


@app.route("/api/stats")
def api_stats():
    with lock:
        return jsonify({"stats": stats, "timeSeries": list(time_series)})


@app.route("/api/packets")
def api_packets():
    packets = []
    if os.path.exists("packets.csv"):
        with open("packets.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                packets.append(row)
    return jsonify(packets[-20:])  # last 20 rows


@app.route("/stream")
def stream():
    """Server-Sent Events — pushes live stats every second."""
    def generate():
        while True:
            with lock:
                data = {
                    "stats": {k: dict(v) for k, v in stats.items()},
                    "timeSeries": list(time_series),
                }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)
    return Response(generate(), mimetype="text/event-stream")


# ── Embedded HTML ───────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⚡ Load Balancer Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#070b14;--card:#ffffff08;--border:#ffffff0d;
  --cyan:#06b6d4;--purple:#8b5cf6;--amber:#f59e0b;--green:#10b981;
  --text:#e2e8f0;--muted:#64748b;
}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh;overflow-x:hidden}
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 70% 50% at 10% 10%,rgba(6,182,212,.13) 0%,transparent 60%),
    radial-gradient(ellipse 60% 45% at 90% 85%,rgba(139,92,246,.12) 0%,transparent 60%);
}
.page{position:relative;z-index:1;max-width:1400px;margin:0 auto;padding:2rem 1.5rem}

/* Header */
header{display:flex;align-items:center;justify-content:space-between;margin-bottom:2.5rem;padding-bottom:1.25rem;border-bottom:1px solid var(--border)}
.logo{display:flex;align-items:center;gap:.75rem}
.logo-icon{width:42px;height:42px;background:linear-gradient(135deg,var(--cyan),var(--purple));border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;flex-shrink:0}
.logo h1{font-size:1.2rem;font-weight:700;background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.logo p{font-size:.72rem;color:var(--muted);margin-top:2px}
.hdr-right{display:flex;align-items:center;gap:1rem}
.live-badge{display:flex;align-items:center;gap:.4rem;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.3);border-radius:999px;padding:.25rem .75rem;font-size:.72rem;font-weight:700;color:var(--green);letter-spacing:.05em}
.live-dot{width:6px;height:6px;background:var(--green);border-radius:50%;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.75)}}
#clock{font-size:.85rem;color:var(--muted);font-variant-numeric:tabular-nums}

/* Server cards */
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:1.25rem;margin-bottom:1.25rem}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1.5rem;position:relative;overflow:hidden;transition:transform .25s,border-color .25s,box-shadow .25s}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:16px 16px 0 0}
.card.c1::before{background:linear-gradient(90deg,var(--cyan),transparent)}
.card.c2::before{background:linear-gradient(90deg,var(--purple),transparent)}
.card.c3::before{background:linear-gradient(90deg,var(--amber),transparent)}
.card:hover{transform:translateY(-4px)}
.card.c1:hover{border-color:rgba(6,182,212,.3);box-shadow:0 12px 40px rgba(6,182,212,.1)}
.card.c2:hover{border-color:rgba(139,92,246,.3);box-shadow:0 12px 40px rgba(139,92,246,.1)}
.card.c3:hover{border-color:rgba(245,158,11,.3);box-shadow:0 12px 40px rgba(245,158,11,.1)}
.card-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem}
.srv-label{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.srv-badge{font-size:.65rem;font-weight:700;padding:.18rem .55rem;border-radius:999px}
.c1 .srv-badge{background:rgba(6,182,212,.15);color:var(--cyan)}
.c2 .srv-badge{background:rgba(139,92,246,.15);color:var(--purple)}
.c3 .srv-badge{background:rgba(245,158,11,.15);color:var(--amber)}
.count{font-size:3rem;font-weight:800;line-height:1;margin-bottom:.5rem;font-variant-numeric:tabular-nums;transition:color .3s}
.c1 .count{color:var(--cyan)}.c2 .count{color:var(--purple)}.c3 .count{color:var(--amber)}
.card-meta{display:flex;justify-content:space-between;font-size:.72rem;color:var(--muted);margin-bottom:.75rem}
.pbar{height:4px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden}
.pfill{height:100%;border-radius:999px;transition:width .5s ease}
.c1 .pfill{background:linear-gradient(90deg,var(--cyan),rgba(6,182,212,.2))}
.c2 .pfill{background:linear-gradient(90deg,var(--purple),rgba(139,92,246,.2))}
.c3 .pfill{background:linear-gradient(90deg,var(--amber),rgba(245,158,11,.2))}

/* Total bar */
.total-row{background:linear-gradient(135deg,rgba(6,182,212,.08),rgba(139,92,246,.08));border:1px solid rgba(6,182,212,.15);border-radius:14px;padding:1rem 1.5rem;display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem}
.total-label{font-size:.875rem;color:var(--muted);font-weight:500}
.total-val{font-size:2rem;font-weight:800;background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-variant-numeric:tabular-nums}

/* Chart */
.panel{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1.5rem;margin-bottom:1.5rem}
.panel-title{font-size:.85rem;font-weight:600;margin-bottom:1.25rem;display:flex;align-items:center;gap:.5rem}
.chart-wrap{position:relative;height:280px}

/* Table */
.tbl-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem}
.tbl-sub{font-size:.72rem;color:var(--muted);font-weight:400}
table{width:100%;border-collapse:collapse;font-size:.8rem}
thead th{text-align:left;padding:.65rem 1rem;font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);border-bottom:1px solid var(--border)}
tbody tr{border-bottom:1px solid rgba(255,255,255,.03);transition:background .15s}
tbody tr:hover{background:rgba(255,255,255,.03)}
tbody td{padding:.6rem 1rem;color:var(--text)}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.65rem;font-weight:700}
.syn{background:rgba(6,182,212,.15);color:var(--cyan)}
.blocked{background:rgba(239,68,68,.15);color:#ef4444}
.empty{text-align:center;padding:2rem;color:var(--muted);font-size:.875rem}
</style>
</head>
<body>
<div class="page">

  <header>
    <div class="logo">
      <div class="logo-icon">⚡</div>
      <div>
        <h1>Load Balancer Dashboard</h1>
        <p>Real-time traffic monitoring · web1 · web2 · web3</p>
      </div>
    </div>
    <div class="hdr-right">
      <div class="live-badge"><div class="live-dot"></div>LIVE</div>
      <div id="clock">--:--:--</div>
    </div>
  </header>

  <div class="cards">
    <div class="card c1">
      <div class="card-hdr"><span class="srv-label">🖥 Server 1</span><span class="srv-badge">web1</span></div>
      <div class="count" id="cnt1">0</div>
      <div class="card-meta"><span>requests</span><span id="last1">Last hit: —</span></div>
      <div class="pbar"><div class="pfill" id="bar1" style="width:0%"></div></div>
    </div>
    <div class="card c2">
      <div class="card-hdr"><span class="srv-label">🖥 Server 2</span><span class="srv-badge">web2</span></div>
      <div class="count" id="cnt2">0</div>
      <div class="card-meta"><span>requests</span><span id="last2">Last hit: —</span></div>
      <div class="pbar"><div class="pfill" id="bar2" style="width:0%"></div></div>
    </div>
    <div class="card c3">
      <div class="card-hdr"><span class="srv-label">🖥 Server 3</span><span class="srv-badge">web3</span></div>
      <div class="count" id="cnt3">0</div>
      <div class="card-meta"><span>requests</span><span id="last3">Last hit: —</span></div>
      <div class="pbar"><div class="pfill" id="bar3" style="width:0%"></div></div>
    </div>
  </div>

  <div class="total-row">
    <span class="total-label">📦 Total Requests Handled</span>
    <span class="total-val" id="total">0</span>
  </div>

  <div class="panel">
    <div class="panel-title">📈 Requests Over Time</div>
    <div class="chart-wrap"><canvas id="chart"></canvas></div>
  </div>

  <div class="panel">
    <div class="tbl-hdr">
      <span class="panel-title" style="margin:0">🔍 Sniffed Packets</span>
      <span class="tbl-sub">Last 20 from packets.csv · refreshes every 5s</span>
    </div>
    <div id="packets-wrap"><div class="empty">Loading packet data…</div></div>
  </div>

</div>

<script>
// Clock
setInterval(()=>{ document.getElementById('clock').textContent = new Date().toLocaleTimeString(); }, 1000);

// Chart.js
const ctx = document.getElementById('chart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label:'web1', data:[], borderColor:'#06b6d4', backgroundColor:'rgba(6,182,212,.08)', borderWidth:2, pointRadius:3, pointBackgroundColor:'#06b6d4', tension:.4, fill:true },
      { label:'web2', data:[], borderColor:'#8b5cf6', backgroundColor:'rgba(139,92,246,.08)', borderWidth:2, pointRadius:3, pointBackgroundColor:'#8b5cf6', tension:.4, fill:true },
      { label:'web3', data:[], borderColor:'#f59e0b', backgroundColor:'rgba(245,158,11,.08)', borderWidth:2, pointRadius:3, pointBackgroundColor:'#f59e0b', tension:.4, fill:true },
    ]
  },
  options: {
    responsive:true, maintainAspectRatio:false,
    interaction:{ mode:'index', intersect:false },
    plugins:{
      legend:{ labels:{ color:'#94a3b8', font:{ family:'Inter', size:12 }, boxWidth:12, padding:20 } },
      tooltip:{ backgroundColor:'#0f172a', borderColor:'rgba(255,255,255,.1)', borderWidth:1, titleColor:'#e2e8f0', bodyColor:'#94a3b8', padding:12 }
    },
    scales:{
      x:{ ticks:{ color:'#475569', font:{family:'Inter',size:11}, maxTicksLimit:10 }, grid:{ color:'rgba(255,255,255,.04)' } },
      y:{ ticks:{ color:'#475569', font:{family:'Inter',size:11} }, grid:{ color:'rgba(255,255,255,.04)' }, beginAtZero:true }
    }
  }
});

// SSE
const es = new EventSource('/stream');
es.onmessage = e => {
  const { stats, timeSeries } = JSON.parse(e.data);
  const w1=stats.web1.count, w2=stats.web2.count, w3=stats.web3.count;
  const total = w1+w2+w3;
  const mx = Math.max(w1,w2,w3,1);

  document.getElementById('cnt1').textContent = w1;
  document.getElementById('cnt2').textContent = w2;
  document.getElementById('cnt3').textContent = w3;
  document.getElementById('total').textContent = total;
  document.getElementById('last1').textContent = 'Last hit: '+stats.web1.last;
  document.getElementById('last2').textContent = 'Last hit: '+stats.web2.last;
  document.getElementById('last3').textContent = 'Last hit: '+stats.web3.last;
  document.getElementById('bar1').style.width = (w1/mx*100)+'%';
  document.getElementById('bar2').style.width = (w2/mx*100)+'%';
  document.getElementById('bar3').style.width = (w3/mx*100)+'%';

  if(timeSeries.length){
    chart.data.labels = timeSeries.map(p=>p.time);
    chart.data.datasets[0].data = timeSeries.map(p=>p.web1);
    chart.data.datasets[1].data = timeSeries.map(p=>p.web2);
    chart.data.datasets[2].data = timeSeries.map(p=>p.web3);
    chart.update('none');
  }
};

// Packets table
function loadPackets(){
  fetch('/api/packets').then(r=>r.json()).then(pkts=>{
    const wrap = document.getElementById('packets-wrap');
    if(!pkts.length){ wrap.innerHTML='<div class="empty">No packets captured yet. Run sniffer.py to start logging.</div>'; return; }
    const rows = [...pkts].reverse().map(p=>`
      <tr>
        <td>${(p.timestamp||'—').split('T')[1]?.split('.')[0]||'—'}</td>
        <td>${p.src_ip||'—'}</td>
        <td>${p.dst_ip||'—'}</td>
        <td>${p.src_port||'—'}</td>
        <td><span class="badge ${p.type==='SYN'?'syn':'blocked'}">${p.type||'—'}</span></td>
      </tr>`).join('');
    wrap.innerHTML=`<table>
      <thead><tr><th>Time</th><th>Src IP</th><th>Dst IP</th><th>Port</th><th>Type</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  });
}
loadPackets();
setInterval(loadPackets, 5000);
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("Starting background log monitors...")
    for container in stats:
        t = threading.Thread(target=stream_logs, args=(container,), daemon=True)
        t.start()

    ts = threading.Thread(target=record_timeseries, daemon=True)
    ts.start()

    print("✅ Dashboard running at http://localhost:5050")
    app.run(debug=False, threaded=True, host="0.0.0.0", port=5050)
