const text=document.getElementById("newsText"),result=document.getElementById("result"), 
count=document.getElementById("charCount"),button=document.getElementById("checkButton"), 
deleteButton=document.getElementById("deleteButton"); 
 
function sources(title,list){ 
    return list?.length?`<div class="sources-section"><h3>${title}</h3><div class="sources-list">${list.map(s=>`<div class="source-card"><h4>${s.source||"Unknown Source"}</h4><p class="source-title">${s.title||"No title available"}</p><a href="${s.link}" target="_blank">Read Source →</a></div>`).join("")}</div></div>`:""; 
} 
 
async function analyze(){ 
    const content=text.value.trim(); 
    if(!content)return show(result,"Analysis Result","Please enter a news article or claim first."); 
    show(result,"Analysis Result","Analyzing your content..."); 
 
    try{ 
        const r=await fetch("/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:content})}); 
        if(!r.ok)throw Error(); 
        const d=await r.json(); 
 
        const verdict=(d.result||"Unknown").toLowerCase(); 
        const status=verdict.includes("misinformation")?"danger":verdict.includes("reliable")?"safe":"neutral"; 
 
        result.innerHTML=` 
        <div class="url-result"> 
        <div class="url-verdict ${status}"> 
            <span>${d.result}</span> 
            <small>${d.evidence_strength||"Unknown"} Evidence</small> 
        </div> 
        <div class="confidence"> 
        <div class="confidence-head"> 
            <strong>AI Confidence</strong> 
            <strong>${d.confidence||0}%</strong> 
        </div> 
        <div class="confidence-bar"> 
            <div style="width:${d.confidence||0}%"></div> 
        </div> 
        </div> 
        <div class="analysis-details"> 
            <p><strong>Evidence:</strong> ${d.evidence_strength||"Unknown"}</p> 
            <p><strong>Supporting:</strong> ${d.supporting_sources?.length||0}</p> 
            <p><strong>Contradicting:</strong> ${d.contradicting_sources?.length||0}</p> 
            <p><strong>Credible Sources:</strong> ${d.credible_sources||0}</p> 
            <p><strong>Independent Sources:</strong> ${d.independent_sources||0}</p> 
        </div> 
        <div class="result-message"> 
            <p>${d.message||""}</p> 
        </div> 
        ${sources("Supporting Sources",d.supporting_sources)} 
        ${sources("Contradicting Sources",d.contradicting_sources)} 
        ${sources("Other Relevant Sources",d.other_sources)} 
        </div>`; 
 
    }catch(e){show(result,"Analysis Error","Unable to connect to the TruthLens server.")} 
} 
 
function show(box,title,message){ 
    box.style.display="block"; 
    box.innerHTML=`<h2>${title}</h2><p>${message}</p>`; 
    box.scrollIntoView({behavior:"smooth"}); 
} 
 
button.addEventListener("click",analyze); 
text.addEventListener("input",()=>count.textContent=text.value.length); 
 
text.addEventListener("keydown",e=>{ 
    if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();analyze()} 
    if(e.key==="Delete"&&text.value)deleteNews(); 
}); 
 
function deleteNews(){ 
    text.value="";count.textContent="0";result.style.display="none";result.innerHTML="";text.focus(); 
} 
 
deleteButton.addEventListener("click",deleteNews); 
 
 
const url=document.getElementById("urlText"),urlResult=document.getElementById("urlResult"), 
urlButton=document.getElementById("urlButton"),urlDelete=document.getElementById("urlDeleteButton"); 
 
async function checkURL(){ 
const content=url.value.trim(); 
if(!content)return show(urlResult,"URL Analysis","Please enter a URL first."); 
show(urlResult,"URL Analysis","Checking your URL..."); 
 
try{ 
    const r=await fetch("/check-url",{ 
        method:"POST", 
        headers:{"Content-Type":"application/json"}, 
        body:JSON.stringify({url:content}) 
    }); 
 
    if(!r.ok)throw Error(); 
 
    const d=await r.json(); 
 
    const verdict=d.result||"Unknown"; 
    const confidence=d.confidence||0; 
 
    let status=""; 
    if(verdict.toLowerCase().includes("phishing")||verdict.toLowerCase().includes("unsafe")||verdict.toLowerCase().includes("malicious")){ 
        status="danger"; 
    } 
 
    urlResult.innerHTML=` 
    <div class="url-result"> 
 
        <div class="url-verdict ${status}"> 
            <span>${verdict}</span> 
            <small>${d.risk||"Unknown"} Risk</small> 
        </div> 
 
        <div class="confidence"> 
            <div class="confidence-head"> 
                <strong>Detection Confidence</strong> 
                <strong>${confidence}%</strong> 
            </div> 
 
            <div class="confidence-bar"> 
                <div style="width:${confidence}%"></div> 
            </div> 
        </div> 
 
        <div class="analysis-details"> 
            <p><strong>AI Confidence:</strong> ${confidence}%</p> 
            <p><strong>Risk Level:</strong> ${d.risk||"Unknown"}</p> 
        </div> 
 
        <div class="sources-section"> 
            <h3>Reasons</h3> 
            <div class="sources-list"> 
                ${(d.reasons||[]).map(reason=>` 
                    <div class="source-card"> 
                        <p class="source-title">${reason}</p> 
                    </div> 
                `).join("")} 
            </div> 
        </div> 
 
    </div>`; 
}catch(e){ 
    show(urlResult,"URL Analysis Error","Unable to connect to the TruthLens server."); 
} 
} 
 
function deleteURL(){ 
    url.value="";urlResult.style.display="none";urlResult.innerHTML="";url.focus(); 
} 
 
urlButton.addEventListener("click",checkURL); 
urlDelete.addEventListener("click",deleteURL); 
url.addEventListener("keydown",e=>{ 
    if(e.key==="Enter"){e.preventDefault();checkURL()} 
}); 
document.querySelector('a[href="#checker"]').onclick=()=>setTimeout(()=>document.getElementById("newsText").focus(),500); 
document.querySelector('a[href="#url-checker"]').onclick=()=>setTimeout(()=>document.getElementById("urlText").focus(),500); 