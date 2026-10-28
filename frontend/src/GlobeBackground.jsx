import React, { useEffect, useRef } from 'react';

// Decorative rotating Earth with recognizable, simplified continent silhouettes.
// Coordinates are approximate geographic outlines (longitude, latitude).
const LAND = [
  [[-168,70],[-150,60],[-135,58],[-125,49],[-124,40],[-116,30],[-105,22],[-97,17],[-90,15],[-83,8],[-77,8],[-80,20],[-97,28],[-105,45],[-123,55],[-140,60],[-155,66]],
  [[-73,60],[-52,60],[-42,72],[-52,83],[-65,80],[-72,70]],
  [[-81,12],[-70,10],[-60,5],[-50,-2],[-35,-8],[-40,-22],[-52,-35],[-68,-56],[-76,-38],[-80,-10]],
  [[-11,36],[-7,50],[5,58],[25,70],[45,68],[58,58],[80,60],[100,70],[130,60],[160,58],[178,50],[155,42],[140,35],[130,20],[120,5],[105,-5],[95,5],[80,8],[70,20],[55,25],[45,35],[30,35],[20,40],[8,36]],
  [[-17,35],[5,37],[30,30],[42,12],[35,-5],[25,-20],[15,-35],[0,-34],[-10,-15],[-17,5]],
  [[-10,58],[-6,50],[2,43],[15,36],[30,40],[40,52],[28,62],[10,70],[-2,65]],
  [[35,31],[52,28],[60,15],[50,5],[42,12]],
  [[68,25],[78,8],[90,7],[95,18],[85,28],[76,32]],
  [[95,20],[110,20],[122,5],[135,-5],[125,-10],[110,0]],
  [[112,-11],[130,-10],[145,-18],[154,-28],[145,-39],[125,-44],[114,-33]],
  [[130,32],[142,40],[146,35],[140,30]],
  [[47,-13],[51,-17],[49,-26],[44,-23]],
  [[-24,64],[-13,63],[-16,67],[-22,68]]
];
function insidePolygon(lon, lat, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i], [xj, yj] = polygon[j];
    const intersects = ((yi > lat) !== (yj > lat)) &&
      (lon < ((xj - xi) * (lat - yi)) / ((yj - yi) || 1e-9) + xi);
    if (intersects) inside = !inside;
  }
  return inside;
}
function isLand(lon, lat) { return LAND.some(poly => insidePolygon(lon, lat, poly)); }

export default function GlobeBackground() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    if (!ctx) return undefined;
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let frame = 0, rotation = -0.45, width = 0, height = 0, dpr = 1;
    const points = [];
    for (let lat = -82; lat <= 82; lat += 3.7) {
      const count = Math.max(10, Math.round(82 * Math.cos((lat * Math.PI) / 180)));
      for (let i = 0; i < count; i++) {
        const lon = -180 + (360 * i) / count + (lat % 7.4 ? 1.2 : 0);
        points.push({ lon: lon * Math.PI / 180, lat: lat * Math.PI / 180, land: isLand(lon, lat * 1) });
      }
    }
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      width = rect.width; height = rect.height;
      canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      const accent = getComputedStyle(document.documentElement).getPropertyValue('--a1-accent').trim() || '#8B5CF6';
      const r = Math.min(width, height) * 0.405;
      const cx = width * 0.5, cy = height * 0.5;
      const glow = ctx.createRadialGradient(cx, cy, r * 0.42, cx, cy, r * 1.28);
      glow.addColorStop(0, `${accent}16`); glow.addColorStop(.7, `${accent}08`); glow.addColorStop(1, `${accent}00`);
      ctx.fillStyle = glow; ctx.fillRect(0, 0, width, height);
      // faint ocean sphere
      const ocean = ctx.createRadialGradient(cx-r*.32, cy-r*.38, r*.08, cx, cy, r*1.05);
      ocean.addColorStop(0, 'rgba(65,105,155,.13)'); ocean.addColorStop(.75, 'rgba(12,25,45,.08)'); ocean.addColorStop(1, 'rgba(4,9,18,.02)');
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.fillStyle = ocean; ctx.fill();
      // Atmospheric edge
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = `${accent}55`; ctx.lineWidth = 1.15; ctx.stroke();
      for (const p of points) {
        const lon = p.lon + rotation, cosLat = Math.cos(p.lat);
        const x3 = cosLat * Math.sin(lon), y3 = Math.sin(p.lat), z3 = cosLat * Math.cos(lon);
        if (z3 < -.04) continue;
        const x = cx + x3*r, y = cy - y3*r, facing = Math.max(0,z3);
        const land = p.land;
        const alpha = (land ? .26 : .035) + facing * (land ? .62 : .11);
        const size = land ? 1.05 + facing*.42 : .48 + facing*.18;
        ctx.beginPath(); ctx.arc(x,y,size,0,Math.PI*2);
        ctx.fillStyle = land ? `${accent}${Math.round(Math.min(.9,alpha)*255).toString(16).padStart(2,'0')}` : `rgba(135,177,225,${alpha})`;
        ctx.fill();
      }
      // subtle latitude/longitude wireframe for geographic context
      ctx.save(); ctx.beginPath(); ctx.arc(cx,cy,r*.995,0,Math.PI*2); ctx.clip();
      ctx.strokeStyle = `${accent}13`; ctx.lineWidth = .65;
      for (const lat of [-60,-30,0,30,60]) {
        const yy = cy - Math.sin(lat*Math.PI/180)*r;
        const rx = r*Math.cos(lat*Math.PI/180);
        ctx.beginPath(); ctx.ellipse(cx,yy,rx,r*.045,0,0,Math.PI*2); ctx.stroke();
      }
      for (const f of [.25,.5,.75]) { ctx.beginPath(); ctx.ellipse(cx,cy,r*f,r,0,0,Math.PI*2); ctx.stroke(); }
      ctx.restore();
      if (!reduceMotion) rotation += .00125;
      frame = window.requestAnimationFrame(draw);
    };
    resize();
    const observer = new ResizeObserver(resize); observer.observe(canvas);
    frame = window.requestAnimationFrame(draw);
    return () => { window.cancelAnimationFrame(frame); observer.disconnect(); };
  }, []);
  return <canvas ref={canvasRef} className="a1-globe-background" aria-hidden="true" />;
}
