import {useEffect,useRef} from 'react'
export interface SSEEvent {run_id:string;status:'SUBMITTED'|'NEEDS_INPUT'|'FAILED';payload:Record<string,unknown>}
export function useSSE(onEvent:(event:SSEEvent)=>void){const ref=useRef(onEvent);ref.current=onEvent;useEffect(()=>{const es=new EventSource('/events');es.addEventListener('apply_update',(event)=>{try{ref.current(JSON.parse((event as MessageEvent).data))}catch{}});return()=>es.close()},[])}
