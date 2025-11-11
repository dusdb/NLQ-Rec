import React, { useState } from 'react';
import './App.css';

// 1. docx 및 file-saver 라이브러리 (그대로 유지)
import { Document, Packer, Paragraph, TextRun, HeadingLevel } from 'docx';
import { saveAs } from 'file-saver';

// --- Mock Data 생성 함수 (원본과 동일) ---
function generateFullMockPanelList(count, queryType = 'base') {
    const fullList = [];
    const jobs = ['IT 기획자', '마케터', '디자이너', '개발자', '금융업', '데이터 분석가', '프리랜서', '학생'];
    const locations = ['서울 강남구', '경기 성남시', '서울 마포구', '서울 서초구', '경기 판교', '서울 송파구'];
    let baseInterests = ['운동'];
    if (queryType === 'cashback') baseInterests.push('포인트/캐시백');
    else if (queryType === 'chatbot') baseInterests.push('AI 챗봇');
    else if (queryType === 'both') baseInterests.push('포인트/캐시백', 'AI 챗봇');
    for (let i = 0; i < count; i++) {
        const id = `P-${Math.floor(Math.random() * 90000) + 10000}`;
        const age = 30 + (i % 10);
        const gender = (i % 2 === 0) ? '남성' : '여성';
        const location = locations[i % locations.length];
        const job = jobs[i % jobs.length];
        let interests = [...baseInterests];
        if (i % 3 === 0) interests.push('재테크');
        if (i % 4 === 0) interests.push('맛집탐방');
        if (i % 5 === 0) interests.push('OTT시청');
        interests = [...new Set(interests)]; 
        fullList.push({ id, age, gender, location, job, interests, bio: `${job}입니다. ${interests.join(', ')}에 관심이 많습니다.` });
    }
    return fullList;
}

// 2. Mock 응답 함수 - '단순 인사이트'와 'AI 전략' 둘 다 생성
function generateMockResponse(query) { 
    const lowerQuery = query.toLowerCase();
    const filterTags = [];
    if (lowerQuery.includes('30대')) filterTags.push({ label: '나이', value: '30-39세', queryPart: '30대' });
    if (lowerQuery.includes('직장인')) filterTags.push({ label: '직업', value: '직장인', queryPart: '직장인' });
    if (lowerQuery.includes('운동')) filterTags.push({ label: '관심사', value: '운동', queryPart: '운동' });
    if (lowerQuery.includes('포인트/캐시백')) filterTags.push({ label: '추가 관심사', value: '포인트/캐시백', queryPart: '포인트/캐시백' });
    if (lowerQuery.includes('ai 챗봇')) filterTags.push({ label: '추가 라이프스타일', value: 'AI 챗봇 사용자', queryPart: 'AI 챗봇' });
    let totalCount;
    const countMatch = query.match(/(\d+)\s*명/);
    let queryType = 'base';
    if (lowerQuery.includes('포인트/캐시백') && lowerQuery.includes('ai 챗봇')) { totalCount = 30; queryType = 'both'; }
    else if (lowerQuery.includes('포인트/캐시백')) { totalCount = 45; queryType = 'cashback'; }
    else if (lowerQuery.includes('ai 챗봇')) { totalCount = 60; queryType = 'chatbot'; }
    else if (countMatch && countMatch[1]) { totalCount = parseInt(countMatch[1], 10); queryType = 'base'; }
    else { totalCount = 100; queryType = 'base'; }

    // --- [여기가 수정되었습니다] ---
    // if/else 로직을 삭제하고, 항상 두 개의 추천을 모두 생성합니다.
    let recommendations = [
        { id: 'rec-001', text: "이 그룹은 평균보다 '포인트/캐시백 혜택' 선호도가 3.2배 높습니다.", action: { buttonText: "+ '포인트/캐시백 선호' 조건 추가하기", data: { type: 'interest', value: '포인트/캐시백', queryPart: '포인트/캐시백' }}},
        { id: 'rec-002', text: "이 그룹의 78%가 'AI 챗봇'을 주 3회 이상 사용합니다.", action: { buttonText: "+ 'AI 챗봇 사용자' 조건 추가하기", data: { type: 'lifestyle', value: 'ai_chatbot_user', queryPart: 'AI 챗봇' }}}
    ];
    // --- [수정 끝] ---
    
    const strategyCards = generateMockStrategyReport(query);
    const currentFullPanelList = generateFullMockPanelList(totalCount, queryType);
    const samplePanels = currentFullPanelList.slice(0, 3);
    return { totalCount, filterTags, samplePanels, recommendations, strategyCards, currentFullPanelList };
}

// 3. AI 전략 보고서 Mock 데이터 생성 함수
function generateMockStrategyReport(query) {
    if (query.length < 3) return []; 
    const report1 = {
        id: 'strategy-001',
        strategyName: "건강 구독 기반 AI 헬스 코치",
        coreTarget: "30대 여성 직장인, 스마트워치 사용자",
        strategyType: "제품 전략",
        keywords: "건강관리 / 구독 / 개인화",
        effect: "지속적 고객 접점(ARR) 확보",
        report: {
            projectName: "건강 구독 기반 AI 헬스 코치 서비스",
            problemDefinition: "바쁜 직장인은 건강관리의 필요성을 인식하지만, 지속적 실천과 맞춤형 루틴 제공의 부재로 건강관리 실행률이 낮음.",
            coreValue: "'꾸준함을 디자인한다' — 데이터 기반 개인화된 건강 루틴 제공",
            serviceConcept: "AI가 개인의 활동/소비 데이터를 기반으로 영양/운동/휴식 루틴을 자동 큐레이션하는 맞춤형 구독 서비스.",
            targetPanel: "수도권 30대 여성 직장인 / 스마트워치 사용자 / 헬스/건강 관심군",
            insightReason: "이 그룹은 스마트워치 보유율 64%, 헬스 관련 소비 비율 1.8배, '꾸준함' 관련 키워드 사용 빈도 2.3배 높음.",
            timeChange: "2023→2025년 '건강관리' 키워드 언급률 +26% 상승, '홈트레이닝' 관련 응답 1.6배 증가.",
            strategyProposal: ["1. 스마트워치 연동 헬스 앱 구독 출시 (MVP)", "2. 직장인 대상 웰니스 캠페인 (B2B)", "3. AI 기반 일일 루틴 피드백 기능 추가"]
        }
    };
    if (query.includes('운동') || query.includes('직장인')) { return [report1]; }
    return [];
}


/**
 * 4. Word(.docx) 다운로드 생성 함수
 */
async function handleDownloadDocx(reportData) {
    if (!reportData) { alert("보고서 데이터가 없습니다."); return; }
    console.log("DOCX 생성 시작:", reportData);
    
    // 텍스트를 Paragraph 배열로 쉽게 변환하는 헬퍼 함수
    const createSection = (title, text) => {
        const paragraphs = [
            // 섹션 제목
            new Paragraph({
                children: [
                    new TextRun({
                        text: title,
                        bold: true,
                        size: 32, // 16pt (16 * 2)
                        color: "000000",
                        font: "맑은 고딕",
                    }),
                ],
                heading: HeadingLevel.HEADING_1,
            })
        ];
        
        // 텍스트가 배열(전략 제안)인 경우와 일반 문자열인 경우 분리
        // 본문
        if (Array.isArray(text)) {
            // '추천 전략 제안' 같은 글머리 기호 목록
            paragraphs.push(
                ...text.map(item => new Paragraph({
                    children: [new TextRun({
                        text: item,
                        size: 24, // 12pt
                        font: "맑은 고딕",
                    })], 
                    bullet: { level: 0 },
                }))
            );
        } else if (text) {
            // '문제 정의' 같은 일반 텍스트
            const lines = text.split("\n");
            paragraphs.push(
                ...lines.map(line => new Paragraph({
                    children: [new TextRun({ 
                        text: line, 
                        size: 24, // 12pt
                        font: "맑은 고딕",
                    })],
                }))
            );
        }

        paragraphs.push(new Paragraph({children: [new TextRun({ text: "", font: "맑은 고딕" })]}));
        paragraphs.push(new Paragraph({children: [new TextRun({ text: "", font: "맑은 고딕" })]}));
        
        return paragraphs;
    };

    try {
        const sections = [
            ...createSection("추천 타겟 패널", reportData.targetPanel),
            ...createSection("제안 이유 (인사이트 근거)", reportData.insightReason),
            ...createSection("시간 흐름에 따른 변화", reportData.timeChange),
            ...createSection("문제 정의", reportData.problemDefinition),
            ...createSection("핵심 가치", reportData.coreValue),
            ...createSection("서비스 컨셉", reportData.serviceConcept),
            ...createSection("추천 전략 제안", reportData.strategyProposal),
        ];

        const doc = new Document({
            sections: [{
                properties: {},
                children: [
                    // --- 문서 제목 ---
                    new Paragraph({
                        children: [
                            new TextRun({
                                text: reportData.projectName,
                                bold: true,
                                size: 44, // 24pt
                                color: "000000",
                                font: "맑은 고딕",
                            }),
                        ],
                        heading: HeadingLevel.TITLE,
                        alignment: 'center', // (docx 라이브러리 버전에 따라 AlignmentType.CENTER)
                        spacing: { after: 480 },
                    }),

                    new Paragraph({ children: [new TextRun({ text: "", font: "맑은 고딕" })]}),
                    // --- 각 섹션 ---
                    ...sections.flat(), // (중첩 배열을 1차원으로 풂)
                ],
            }],
        });

        // Blob 생성 및 파일 다운로드 (file-saver)
        const blob = await Packer.toBlob(doc);
        saveAs(blob, "AI_전략_제안서_초안.docx");

    } catch (error) {
        console.error("DOCX 생성 중 오류 발생:", error);
        alert("보고서 파일 생성에 실패했습니다.");
    }
}


// --- React 컴포넌트 정의 ---

/**
 * 1. 메인 App 컴포넌트
 */
function App() {
    // --- 상태 정의 (useState) ---
    const [query, setQuery] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSearched, setIsSearched] = useState(false);
    
    const [filterTags, setFilterTags] = useState([]);
    const [totalCount, setTotalCount] = useState(0);
    const [samplePanels, setSamplePanels] = useState([]);
    const [currentFullPanelList, setCurrentFullPanelList] = useState([]);
    
    // 2가지 인사이트 상태
    const [recommendations, setRecommendations] = useState([]);
    const [strategyCards, setStrategyCards] = useState([]);
    
    // 2가지 모달 상태
    const [isPanelModalOpen, setIsPanelModalOpen] = useState(false);
    const [selectedPanel, setSelectedPanel] = useState(null);
    const [isStrategyModalOpen, setIsStrategyModalOpen] = useState(false);
    const [selectedStrategy, setSelectedStrategy] = useState(null);

    // '전체 패널 보기' 뷰 상태
    const [isAllPanelsViewVisible, setIsAllPanelsViewVisible] = useState(false);

    // '전체 패널 보기' 화면이 닫히는 애니메이션 중인지 추적
    const [isAllPanelsExiting, setIsAllPanelsExiting] = useState(false);

    // --- 핵심 로직 (이벤트 핸들러) ---
    const handleSearch = (queryToSearch) => {
        if (!queryToSearch && filterTags.length === 0) {
             if (queryToSearch === "") clearResults();
             return;
        }
        setIsLoading(true);
        setIsSearched(true); 
        console.log(`백엔드로 전송할 쿼리: "${queryToSearch}"`);

        // 비동기 API 호출 시뮬레이션
        setTimeout(() => {
            const mockResponse = generateMockResponse(queryToSearch);
            setTotalCount(mockResponse.totalCount);
            setFilterTags(mockResponse.filterTags);
            setSamplePanels(mockResponse.samplePanels);
            setCurrentFullPanelList(mockResponse.currentFullPanelList);
            setRecommendations(mockResponse.recommendations);
            setStrategyCards(mockResponse.strategyCards);
            setIsLoading(false);
        }, 1500);
    };

    const clearResults = () => {
        setIsSearched(false);
        setFilterTags([]);
        setTotalCount(0);
        setSamplePanels([]);
        setRecommendations([]);
        setStrategyCards([]);
        setCurrentFullPanelList([]);
    };
    
    // '단순 인사이트' (조건 추가) 클릭 핸들러
    const handleRecommendationClick = (rec) => {
        const actionData = rec.action.data;
        const partToAdd = actionData.queryPart || actionData.value;
        if (query.toLowerCase().includes(partToAdd.toLowerCase())) return; // 중복 추가 방지
        const newQuery = `${query.trim()}, ${partToAdd}`;
        setQuery(newQuery);
        handleSearch(newQuery); // 새 쿼리로 즉시 재검색
    };
    
    // '필터 태그' (제거) 클릭 핸들러
    const handleTagRemove = (tagToRemove) => {
        const regex = new RegExp(`\\s*,?\\s*${tagToRemove.queryPart}\\s*,?`, 'i');
        const newQuery = query.replace(regex, ',').replace(/^,|,$/g, '').replace(/, *,/g, ', ');
        const newQueryTrimmed = newQuery.trim();
        setQuery(newQueryTrimmed);
        handleSearch(newQueryTrimmed); // 새 쿼리로 즉시 재검색
    };

    // --- 모달 핸들러 (2종류) ---
    // 1. 패널 모달 열기 / 닫기
    const openPanelModal = (panel) => {
        setSelectedPanel(panel); // 1. 데이터 먼저 삽입 (아직 안 보임)
        setTimeout(() => {
            setIsPanelModalOpen(true); // 2. (20ms 뒤) '열어라' 명령
        }, 20); // 0초보다 20ms가 브라우저 렌더링에 안전함
    };
    const closePanelModal = () => {
        setIsPanelModalOpen(false); // 1. '닫아라' 명령 (애니메이션 시작)
        setTimeout(() => {
            setSelectedPanel(null); // 2. (300ms 뒤) 데이터 제거 (컴포넌트 소멸)
        }, 300); 
    };

    // 2. 전략 모댤 열기 / 닫기
    const openStrategyModal = (strategy) => {
        setSelectedStrategy(strategy); // 1. 데이터 먼저 삽입
        setTimeout(() => {
            setIsStrategyModalOpen(true); // 2. (20ms 뒤) '열어라' 명령
        }, 20);
    };
    const closeStrategyModal = () => {
        setIsStrategyModalOpen(false); // 1. '닫아라' 명령
        setTimeout(() => {
            setSelectedStrategy(null); // 2. (300ms 뒤) 데이터 제거
        }, 300);
    };

    // --- [새 '전체 패널' 닫기 핸들러 추가] ---
    const handleCloseAllPanels = () => {
        setIsAllPanelsExiting(true); // 1. '사라지는 중' 상태로 변경 (CSS 애니메이션 시작)
        setTimeout(() => {
            // 2. (300ms 뒤) 애니메이션이 끝나면 실제 상태 변경
            setIsAllPanelsViewVisible(false);
            setIsAllPanelsExiting(false);
        }, 300); // CSS 애니메이션 시간과 동일하게 설정
    };

    // --- 뷰 렌더링 로직 ---

    // '전체 패널 보기'가 활성화되면, 그것만 렌더링
    if (isAllPanelsViewVisible || isAllPanelsExiting) {
        return (
            <AllPanelsView
                fullPanelList={currentFullPanelList}
                totalCount={totalCount}
                onBack={handleCloseAllPanels} // 1. 새 닫기 함수 전달
                isExiting={isAllPanelsExiting} // 2. '사라지는 중' 상태 전달
            />
        );
    }

    // 메인 뷰 렌더링
    return (
        <>
            {/* .search-active 클래스로 검색 전/후 상태 제어 */}
            <div className={`container ${isSearched ? 'search-active' : ''}`}>
                
                {/* --- [수정된 헤더] --- */}
                <header className="hero-header">
                    {/* 로고. /public/logo.png에 파일이 있어야 합니다. */}
                    <img src="/logo.png" className="logo" alt="App Logo" />
                    
                    {/* "검색 전"에만 보이는 큰 제목/설명 */}
                    <h1>AI로 잠재 고객을 발견하세요</h1>
                    <p>원하는 타겟을 자연어로 검색하고, AI가 제안하는 마케팅/서비스 전략 인사이트를 확인해보세요.</p>
                    
                    {/* "검색 후"에만 보이는 새 제목 */}
                    <h2 className="app-title-active">AI Panel Insight</h2>
                </header>
                {/* --- [헤더 수정 끝] --- */}


                <section id="control-tower" className="workspace-section">
                    <h2>검색하기 : 원하는 조건을 입력해주세요</h2>
                    <div className="search-wrapper">
                        <input
                            type="text"
                            id="search-input"
                            placeholder="예: 30대 직장인 중 운동에 관심 있는 사람 100명"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyUp={(e) => { if (e.key === 'Enter') handleSearch(query); }}
                        />
                        <button id="search-button" onClick={() => handleSearch(query)}>
                            분석 시작
                        </button>
                    </div>
                    <div id="filter-tags-container">
                        {filterTags.map((tag, index) => (
                            <FilterTag key={index} tag={tag} onRemove={handleTagRemove} />
                        ))}
                    </div>
                </section>

                {/* 로딩 스피너 */}
                {isLoading && <Loader />}

                {/* 검색 결과 */}
                {isSearched && !isLoading && totalCount > 0 && (
                    <div id="results-wrapper" className="visible">
                        
                        {/* 2가지 인사이트 섹션 */}
                        {(recommendations.length > 0 || strategyCards.length > 0) && (
                            <section id="discovery-zone" className="workspace-section">
                                <h2>추천 인사이트</h2>

                                {/* A. 공통 특성 (단순 인사이트) */}
                                {recommendations.length > 0 && (
                                    <div className="discovery-subsection">
                                        <h3>공통 특성</h3>
                                        <div id="recommendations-container">
                                            {recommendations.map((rec) => (
                                                <RecommendationCard
                                                    key={rec.id}
                                                    rec={rec}
                                                    onClick={handleRecommendationClick}
                                                />
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* B. AI 추천 전략 (엣지 서비스) */}
                                {strategyCards.length > 0 && (
                                    <div className="discovery-subsection">
                                        <br></br>
                                        <h3>AI 추천 전략</h3>
                                        <div id="strategy-cards-container">
                                            {strategyCards.map((strategy) => (
                                                <StrategyCard
                                                    key={strategy.id}
                                                    strategy={strategy}
                                                    onClick={openStrategyModal}
                                                />
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </section>
                        )}
                        
                        {/* 패널 분석 결과 */}
                        <section id="main-stage" className="workspace-section">
                            <div className="results-header-wrapper">
                                <h2>분석 결과</h2>
                                <button
                                    id="view-all-panels-btn"
                                    className="view-all-btn"
                                    style={{ display: 'block' }}
                                    onClick={() => setIsAllPanelsViewVisible(true)}
                                >
                                    패널 전체 보기 ({totalCount}명)
                                </button>
                            </div>
                            <p id="results-count">
                                총 <strong>{totalCount}</strong>명 검색됨
                            </p>
                            <div id="panel-spotlight-container">
                                {samplePanels.map((panel) => (
                                    <PanelCard
                                        key={panel.id}
                                        panel={panel}
                                        onDetailClick={openPanelModal}
                                    />
                                ))}
                            </div>
                        </section>
                    </div>
                )}
            </div>
            
            {/* --- 모달 렌더링 (2종류) --- */}
            {selectedPanel && (
                <PanelDetailModal
                isOpen={isPanelModalOpen}
                onClose={closePanelModal}
                panel={selectedPanel}
                />
            )}

            {selectedStrategy && (
                <StrategyDetailModal
                isOpen={isStrategyModalOpen}
                onClose={closeStrategyModal}
                strategy={selectedStrategy}
                />
            )}
        </>
    );
}

// --- 하위 컴포넌트들 ---

/**
 * 2. '전체 패널 보기' 뷰
 */
function AllPanelsView({ fullPanelList, totalCount, onBack, isExiting }) {
    const [selectedPanel, setSelectedPanel] = useState(null);

    const viewClassName = `all-panels-view-container ${isExiting ? 'all-panels-view-exiting' : ''}`;
   
    return (
        <div id="all-panels-view" className={viewClassName} style={{ display: 'flex' }}>
            <header className="all-panels-header">
                <button id="back-to-results-btn" className="back-btn" onClick={onBack}>&larr;</button>
                <h2 id="all-panels-title">전체 패널 목록 ({totalCount}명)</h2>
            </header>
            <div className="all-panels-content">
                <div id="all-panels-list" className="panel-list-column">
                    {fullPanelList.length > 0 ? (
                        fullPanelList.map(panel => (<PanelCard key={panel.id} panel={panel} onDetailClick={setSelectedPanel} />))
                    ) : ( <p>표시할 패널이 없습니다.</p> )}
                </div>
                <div id="all-panels-detail" className="panel-detail-column">
                    <PanelDetail 
                        key={selectedPanel ? selectedPanel.id : 'placeholder'} 
                        panel={selectedPanel} 
                    />
                </div>
            </div>
        </div>
    );
}

/**
 * 3. 패널 상세 모달
 */
function PanelDetailModal({ isOpen, onClose, panel }) {
    const overlayClasses = `modal-overlay ${isOpen ? 'visible' : ''}`;
    const modalClasses = `panel-detail-modal ${isOpen ? 'open' : ''}`;
    return (
        <>
            <div id="modal-overlay" className={overlayClasses} onClick={onClose}></div>
            <div id="panel-detail-modal" className={modalClasses}>
                <div className="modal-header">
                    <h3>패널 상세 정보</h3>
                    <button id="panel-modal-close-btn" onClick={onClose}>&times;</button>
                </div>
                <div id="modal-content">
                    {panel ? <PanelDetail panel={panel} /> : <div className="placeholder-text">...</div>}
                </div>
            </div>
        </>
    );
}

/**
 * 7. (복원) '단순 인사이트' 카드 컴포넌트
 */
function RecommendationCard({ rec, onClick }) {
    return (
        <div className="recommendation-card">
            <p>{rec.text}</p>
            <button onClick={() => onClick(rec)}>
                {rec.action.buttonText}
            </button>
        </div>
    );
}


/**
 * 8. 'AI 전략' 카드 컴포넌트
 */
function StrategyCard({ strategy, onClick }) {
    return (
        <div className="strategy-card">
            <div className="strategy-card-header">
                <span className={`strategy-type ${strategy.strategyType.replace(' ', '-')}`}>{strategy.strategyType}</span>
            </div>
            <div className="strategy-card-body">
                <h3>{strategy.strategyName}</h3>
                <p><strong>핵심 타겟:</strong> {strategy.coreTarget}</p>
                <p><strong>키워드:</strong> {strategy.keywords}</p>
            </div>
            <div className="strategy-card-footer">
                <button onClick={() => onClick(strategy)}>
                    AI 전략 상세 보기
                </button>
            </div>
        </div>
    );
}


/**
 * 9. 'AI 전략 상세' 모달 컴포넌트
 */
function StrategyDetailModal({ isOpen, onClose, strategy }) {
    const reportData = strategy.report;
    
    const onDownloadClick = () => {
        handleDownloadDocx(reportData);
    };

    return (
        <>
            {/* --- [여기가 수정되었습니다!] --- */}
            {/* (id="modal-overlay" 추가) */}
            <div id="modal-overlay" className={`modal-overlay ${isOpen ? 'visible' : ''}`} onClick={onClose}></div>
            {/* --- [수정 끝] --- */}
            
            <div className={`strategy-detail-modal ${isOpen ? 'open' : ''}`}>
                <button id="strategy-modal-close-btn" title="닫기" onClick={onClose}>&times;</button>
                <div className="modal-header">
                    <h3>{reportData?.projectName || "AI 전략 상세 보기"}</h3>
                </div>
                <div className="strategy-modal-content">
                    {reportData ? (
                        <StrategyReportContent report={reportData} />
                    ) : ( <p>전략 데이터를 불러오는 중입니다...</p> )}
                </div>
                <div className="strategy-modal-footer">
                    <button className="download-btn" onClick={onDownloadClick} disabled={!reportData}>
                        📄 기획서 초안 (Word) 다운로드
                    </button>
                </div>
            </div>
        </>
    );
}

/**
 * 10. 전략 보고서 내용 컴포넌트 (모달 내부)
 */
function StrategyReportContent({ report }) {
    return (
        <div className="report-layout">
            <div className="report-column">
                <div className="report-item"><h4>🎯 추천 타겟 패널</h4><p>{report.targetPanel}</p></div>
                <div className="report-item"><h4>🔍 인사이트 근거 (제안 이유)</h4><p>{report.insightReason}</p></div>
                <div className="report-item"><h4>📈 시간 흐름에 따른 변화</h4><p>{report.timeChange}</p></div>
            </div>
            <div className="report-column">
                <div className="report-item"><h4>🤔 문제 정의</h4>
                    {/* (수정) \n을 <br/> 태그로 변환하여 렌더링 */}
                    <p>
                        {report.problemDefinition.split('\n').map((line, i) => (
                            <React.Fragment key={i}>
                                {line}
                                <br/>
                            </React.Fragment>
                        ))}
                    </p>
                </div>
                <div className="report-item"><h4>💎 핵심 가치</h4><p>{report.coreValue}</p></div>
                <div className="report-item"><h4>🚀 서비스 컨셉</h4><p>{report.serviceConcept}</p></div>
                <div className="report-item"><h4>🔥 추천 전략 제안</h4><ul>{report.strategyProposal.map((item, index) => (<li key={index}>{item}</li>))}</ul></div>
            </div>
        </div>
    );
}


// --- 11. 재사용 컴포넌트들 (기존) ---
function FilterTag({ tag, onRemove }) {
    return (
        <div className="filter-tag" data-query-part={tag.queryPart}>
            <span>{tag.label}: {tag.value}</span>
            <button title="필터 제거" onClick={() => onRemove(tag)}>ⓧ</button>
        </div>
    );
}

function PanelCard({ panel, onDetailClick }) {
    return (
        <div className="panel-card">
            <h4>
                <span>{panel.id}</span>
                <button className="detail-btn" onClick={() => onDetailClick(panel)}>자세히 보기</button>
            </h4>
            <ul>
                <li><strong>나이:</strong> {panel.age}세</li>
                <li><strong>직업:</strong> {panel.job}</li>
                <li><strong>주요 관심사:</strong> {panel.interests.join(', ')}</li>
            </ul>
        </div>
    );
}

function PanelDetail({ panel }) {
    if (!panel) {
        return (
            <div className="panel-detail-wrapper">
                <p className="placeholder-text">왼쪽 목록에서 패널의 '자세히 보기'를 선택하세요.</p>
            </div>
        );
    }
    return (
        <div className="panel-detail-wrapper">
            <div className="profile-section">
                <div className="profile-avatar">P</div>
                <div className="profile-summary">
                    <p className="name">{panel.id}</p>
                    <p>{panel.gender}, {panel.age}세</p>
                    <p>{panel.location}</p>
                </div>
            </div>
            <div className="profile-details">
                <h4>자기소개</h4>
                <p>{panel.bio}</p>
                <h4>상세 정보</h4>
                <ul>
                    <li><strong>직업:</strong> <span>{panel.job}</span></li>
                    <li><strong>주요 관심사:</strong> <span>{panel.interests.join(', ')}</span></li>
                </ul>
            </div>
        </div>
    );
}

function Loader() {
    return <div id="loader" style={{ display: 'block' }}></div>;
}

export default App;