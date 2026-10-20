'use strict';
const pngButton=$('exportPng');
let pngBusy=false;
// Observe the existing export state, including loading and failed requests.
new MutationObserver(()=>{pngButton.disabled=pngBusy||$('export').disabled;}).observe($('export'),{attributes:true,attributeFilter:['disabled']});
pngButton.disabled=$('export').disabled;
pngButton.onclick=async()=>{
 if(pngBusy||!product?.layers[$('layer').value])return;
 const snapshot=product,key=$('layer').value,g=snapshot.layers[key],limits=range(),withCurrent=$('current').checked&&!!snapshot.current;
 const out=document.createElement('canvas');out.width=2400;out.height=2400;
 const pen=out.getContext('2d');pen.fillStyle='#ffffff';pen.fillRect(0,0,out.width,out.height);
 pen.drawImage(canvas,0,230,2400,1920);
 pngBusy=true;pngButton.disabled=true;pngButton.textContent='產製圖片中…';
 try{
  const logo=new Image();logo.src='assets/tfrin-logo.png';await logo.decode();pen.drawImage(logo,28,22,175,175);
  pen.fillStyle='#173e48';pen.font='bold 39px "Microsoft JhengHei",sans-serif';pen.fillText('農業部水產試驗所 鬼頭刀漁海況研究小組',215,83);
  pen.font='bold 43px "Microsoft JhengHei",sans-serif';pen.fillText(labels[key],215,146);
  pen.font='26px "Microsoft JhengHei",sans-serif';pen.fillText(`資料日期 ${snapshot.date} ｜ ${withCurrent?'含同日表面海流':'海況圖層'} ｜ 模型 2.0.0`,215,196);
  const x=1780,y=1900,w=560,h=210;pen.fillStyle='rgba(255,255,255,.96)';pen.fillRect(x,y,w,h);pen.fillStyle='#173e48';pen.font='27px "Microsoft JhengHei",sans-serif';pen.fillText(labels[key],x+24,y+40);
  const ramp=pen.createLinearGradient(x+24,0,x+w-24,0);stops.forEach((c,i)=>ramp.addColorStop(i/4,`rgb(${c.join(',')})`));pen.fillStyle=ramp;pen.fillRect(x+24,y+65,w-48,18);pen.fillStyle='#173e48';pen.font='25px sans-serif';pen.fillText(String(limits[0]),x+24,y+124);pen.textAlign='center';pen.fillText(String((limits[0]+limits[1])/2),x+w/2,y+124);pen.textAlign='right';pen.fillText(`${limits[1]} ${g.unit}`,x+w-24,y+124);pen.textAlign='left';if(withCurrent){pen.font='22px "Microsoft JhengHei",sans-serif';pen.fillText('海流單位 m/s；箭頭方向代表流向',x+24,y+174);}
  pen.fillStyle='#fff';pen.fillRect(0,2160,2400,240);pen.fillStyle='#426461';pen.font='25px "Microsoft JhengHei",sans-serif';
  pen.fillText('資料：JMA GOOS HIMSST / NPRSUBT / NPRSUBC（依圖層） · 底圖：Natural Earth',60,2210);
  pen.fillText('HSI 為未校準相對適合度 0–1；非捕獲機率、魚群位置或漁獲保證。',60,2255);
  pen.fillText(key==='sst'?'SST 等溫線：25、26、27、28°C；缺值保持空白。':'SSS、MLD 尚無實測輸入；海流僅供疊圖。缺值保持空白。',60,2300);
  pen.font='22px sans-serif';pen.fillText('marinechchang-rgb.github.io/mahi-ocean-web/',60,2350);
  const blob=await new Promise((resolve,reject)=>out.toBlob(b=>b?resolve(b):reject(Error('PNG 產製失敗')),'image/png'));
  const dataUrl=out.toDataURL('image/png'),a=$('pngLink');a.href=dataUrl;a.download=`mahi-${snapshot.date}-${key}.png`;$('pngImage').src=dataUrl;$('pngPreview').hidden=false;a.click();$('status').textContent='已產製 2400 × 2400 PNG，含日期、LOGO 與圖例；可展開預覽或再次下載。';
 }catch(e){$('status').textContent='圖片匯出失敗：'+e.message;}
 finally{pngBusy=false;pngButton.disabled=$('export').disabled;pngButton.textContent='下載簡報 PNG';}
};
