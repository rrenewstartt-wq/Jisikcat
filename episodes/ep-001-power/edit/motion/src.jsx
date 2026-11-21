import React from 'react';
import {AbsoluteFill, Composition, interpolate, registerRoot, useCurrentFrame, useVideoConfig} from 'remotion';
import prices from './work/prices.json';

const hours = [0, 8, 8.99, 9, 10, 13, 14, 18, 23.9];
const beats = [0, 3.5, 5.87, 6.4, 9.1, 10.7, 14.27, 15.6, 17.84];
const ink = '#112e33', red = '#ab391d', green = '#006a61';
const x = h => 94 + h * 46;
const y = price => 345 - price * 1.32;

function DayAhead() {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const h = interpolate(frame / fps, beats, hours, {extrapolateRight:'clamp'});
  const hour = Math.floor(h), value = prices[hour], col = value < 0 ? red : green;
  let path = `M${x(0)} ${y(prices[0])}`;
  for (let n=1; n<=hour; n++) path += ` H${x(n)} V${y(prices[n])}`;
  path += ` H${x(h)}`;
  return <AbsoluteFill style={{background:'#f2eddf',color:ink,fontFamily:'Noto Sans CJK KR, sans-serif'}}>
    <div style={{position:'absolute',left:76,top:35,fontSize:23,letterSpacing:1}}>독일·룩셈부르크　 /　 하루 전 전력시장</div>
    <div style={{position:'absolute',left:72,top:105,fontSize:77,fontWeight:800,letterSpacing:-4,color:col}}>{value>0?'+':'−'}{Math.abs(value).toFixed(2)} <span style={{fontSize:31,letterSpacing:0}}>€/MWh</span></div>
    <div style={{position:'absolute',right:91,top:91,textAlign:'right',fontSize:27}}>2024. 05. 12.<br/><b style={{fontSize:41}}>{String(hour).padStart(2,'0')}:00</b></div>
    <svg width="1280" height="720" viewBox="0 0 1280 720" style={{position:'absolute'}}>
      <defs><pattern id="paper" width="23" height="23" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#85928c" opacity=".22"/></pattern></defs>
      <rect y="219" width="1280" height="366" fill="url(#paper)"/>
      {[75,0,-75,-150].map(v=><g key={v}><line x1="94" x2="1200" y1={y(v)} y2={y(v)} stroke={v===0?ink:'#a5b0a5'} strokeWidth={v===0?2:1}/><text x="75" y={y(v)+6} textAnchor="end" fontSize="17" fill={ink}>{v}</text></g>)}
      <path d={path+` V345 H94 Z`} fill={col} opacity=".12"/><path d={path} fill="none" stroke={col} strokeWidth="7" strokeLinejoin="round"/>
      <line x1={x(h)} x2={x(h)} y1="226" y2="555" stroke={col} strokeDasharray="3 7"/>
      <circle cx={x(h)} cy={y(value)} r={10+3*Math.sin(frame*.2)} fill={col} opacity=".25"/><circle cx={x(h)} cy={y(value)} r="7" fill={col}/>
      {[0,6,12,18,23].map(v=><text key={v} x={x(v)} y="582" textAnchor="middle" fontSize="21" fill={ink}>{v}시</text>)}
    </svg><div style={{position:'absolute',bottom:102,left:78,fontSize:17,color:'#455b5b'}}>시간별 거래가격　·　Bundesnetzagentur | SMARD.de</div>
  </AbsoluteFill>;
}
const Root = () => <Composition id="DayAhead" component={DayAhead} width={1280} height={720} fps={24} durationInFrames={429}/>;
registerRoot(Root);
