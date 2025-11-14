import React, { useState } from 'react';
import './App.css';

// 1. docx 및 file-saver 라이브러리
import { 
    Document, Packer, Paragraph, TextRun, HeadingLevel, 
    Table, TableRow, TableCell, WidthType, BorderStyle, AlignmentType 
} from 'docx';
import { saveAs } from 'file-saver';

// --- Mock Data 생성 함수 ---
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

    let recommendations = [
        { id: 'rec-001', text: "이 그룹은 평균보다 '포인트/캐시백 혜택' 선호도가 3.2배 높습니다.", action: { buttonText: "+ '포인트/캐시백 선호' 조건 추가하기", data: { type: 'interest', value: '포인트/캐시백', queryPart: '포인트/캐시백' }}},
        { id: 'rec-002', text: "이 그룹의 78%가 'AI 챗봇'을 주 3회 이상 사용합니다.", action: { buttonText: "+ 'AI 챗봇 사용자' 조건 추가하기", data: { type: 'lifestyle', value: 'ai_chatbot_user', queryPart: 'AI 챗봇' }}}
    ];
    
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
            
            // 공통 정보
            projectName: "건강 구독 기반 AI 헬스 코치 서비스",
            projectSubtitle: "AI를 활용한 개인 맞춤형 루틴형 건강관리 제안서",

            // 섹션 1: 프로젝트 요약
            summaryTable: [
                { th: "프로젝트명",   td: "AI 헬스 코치 (가칭)" },
                { th: "타겟 고객",     td: "수도권 30대 여성 직장인, 스마트워치 사용자, 건강 관심층" },
                { th: "핵심 인사이트", td: "'꾸준함' 관련 키워드 사용률 2.3배 증가, 웰니스 소비 1.8배 상승" },
                { th: "핵심 제안",     td: "AI가 개인의 루틴 데이터를 분석해 지속 가능한 건강 습관을 디자인" }
            ],

            // 섹션 2: 문제 정의
            problemDefinition: "바쁜 직장인들은 건강관리의 필요성을 인식하고 있으나, 지속적 실천과 맞춤형 루틴 관리의 부재로 실행률이 낮습니다. 기존 헬스케어 앱은 일시적 사용에 머무르고 있으며, 구독형 루틴 제공 서비스의 시장 공백이 존재합니다.",

            // 섹션 3: 핵심 가치
            coreValueHighlight: `"꾸준함을 디자인한다"`,
            coreValueText: "데이터 기반 AI 분석으로 개인의 패턴에 최적화된 운동/영양/휴식 루틴을 자동 추천하여 건강한 습관을 형성하게 합니다.",

            // 섹션 4: 인사이트 근거
            insightTable: {
                headers: ["지표", "수치", "의미"],
                rows: [
                    ["스마트워치 보유율", "64%", "건강 관련 데이터 수집 기반 확대"],
                    ["헬스 관련 소비 증가율", "+1.8배", "웰니스 산업 성장세 강화"],
                    ["'꾸준함' 키워드 검색량", "+2.3배", "지속 가능한 루틴화 욕구 증가"],
                    ["'홈트레이닝' 언급량", "+1.6배", "집중적 자기관리 트렌드 강화"]
                ]
            },

            // 섹션 5: 서비스 개요
            serviceTable: {
                headers: ["항목", "내용"],
                rows: [
                    ["서비스 형태", "AI 기반 건강 루틴 구독형 코칭 서비스"],
                    ["핵심 기능", "데이터 분석 / 루틴 자동 추천 / AI 피드백"],
                    ["차별점", "지속성 중심의 구독 + 개인화 루틴 추천 결합"],
                    ["구독 모델", "무료 베이직 / 유료 프리미엄 / 전문가 매칭"]
                ]
            },

            // 섹션 6: 전략 제안
            strategyProposal: [
                "스마트워치 연동형 MVP 출시",
                "B2B 제휴 (직장인 복지 플랫폼 / 보험사 등)",
                "AI 피드백 기능 및 목표 기반 루틴 강화"
            ],

            // 섹션 7: 기대 효과
            effectTable: {
                headers: ["구분", "정량적 효과", "정성적 효과"],
                rows: [
                    ["사용자", "앱 유지율 +30%", "루틴화 및 건강 동기 부여"],
                    ["기업", "구독 매출 +15%", "브랜드 신뢰도 향상"],
                    ["사회", "건강 실천율 향상", "헬스케어 데이터 활성화"]
                ]
            }
        }
    };
    if (query.includes('운동') || query.includes('직장인')) { return [report1]; }
    return [];
}


// 4. Word(.docx) 다운로드 생성 함수
async function handleDownloadDocx(report) {
    if (!report) return;

    // 스타일 정의
    // 제목 스타일
    const titleStyle = {
        children: [
            new TextRun({
                text: report.projectName || "AI 헬스 코치 (가칭)",
                bold: true,
                size: 48
            })
        ],
        heading: HeadingLevel.TITLE,
        alignment: AlignmentType.CENTER,
    };
    
    // 부제목 스타일
    const subtitleStyle = {
        text: report.projectSubtitle || "AI를 활용한 개인 맞춤형 루틴형 건강관리 제안서",
        heading: HeadingLevel.HEADING_1,
        style: "Subtitle", 
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
    };

    // 섹션 제목 (예: "1 프로젝트 요약")
    const createSectionHeading = (number, text) => {
        return new Paragraph({
            children: [
                new TextRun({ text: `${number} `, size: 32, bold: true }),
                new TextRun({ text: text, size: 32, bold: true }),
            ],
            spacing: { before: 400, after: 200 },
        });
    };

    // 기본 본문
    const createPara = (text) => {
        return new Paragraph({
            children: [new TextRun({ text: text, size: 22 })],
            spacing: { after: 100 },
        });
    };

    const BORDER_STYLE = { style: BorderStyle.SINGLE, size: 1, color: "E0E6ED" };
    const TABLE_BORDERS = { top: BORDER_STYLE, bottom: BORDER_STYLE, left: BORDER_STYLE, right: BORDER_STYLE };

    // 헬퍼: 2열 테이블 생성 (섹션 1, 5)
    const createTwoColTable = (data) => {
        const rows = data.map(item => 
            new TableRow({ 
                children: [
                    new TableCell({ borders: TABLE_BORDERS, children: [createPara(item.th || item[0])] }),
                    new TableCell({ borders: TABLE_BORDERS, children: [createPara(item.td || item[1])] })
                ]
            })
        );
        return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: rows });
    };

    // 헬퍼: 3열 테이블 생성 (섹션 4, 7)
    const createThreeColTable = (data) => {
        const headerRow = new TableRow({ 
            tableHeader: true, 
            children: data.headers.map(header => new TableCell({ borders: TABLE_BORDERS, children: [createPara(header)] })) 
        });
        const dataRows = data.rows.map(row => 
            new TableRow({ 
                children: [
                    new TableCell({ borders: TABLE_BORDERS, children: [createPara(row[0])] }),
                    new TableCell({ borders: TABLE_BORDERS, children: [createPara(row[1])] }),
                    new TableCell({ borders: TABLE_BORDERS, children: [createPara(row[2])] })
                ]
            })
        );
        return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: [headerRow, ...dataRows] });
    };


    // 문서 생성
    const doc = new Document({
        styles: {
            default: { run: { font: "맑은 고딕" } },
            paragraphStyles: [
                { id: "Subtitle", name: "Subtitle", basedOn: "Normal", next: "Normal", run: { size: 28, color: "777777" } },
            ],
        },
        sections: [
            {
                children: [
                    new Paragraph(titleStyle),
                    new Paragraph(subtitleStyle),

                    // 1. 프로젝트 요약
                    createSectionHeading(1, "프로젝트 요약"),
                    createTwoColTable(report.summaryTable),

                    // 2. 문제 정의
                    createSectionHeading(2, "문제 정의"),
                    createPara(report.problemDefinition),

                    // 3. 핵심 가치
                    createSectionHeading(3, "핵심 가치"),
                    new Paragraph({
                        children: [new TextRun({ text: report.coreValueHighlight, size: 26, bold: true, color: "14213D" })],
                        spacing: { after: 100 },
                    }),
                    createPara(report.coreValueText),

                    // 4. 인사이트 근거
                    createSectionHeading(4, "인사이트 근거"),
                    createThreeColTable(report.insightTable),

                    // 5. 서비스 개요
                    createSectionHeading(5, "서비스 개요"),
                    createTwoColTable(report.serviceTable.rows), // 헤더가 2개 뿐이라 rows만 사용

                    // 6. 전략 제안
                    createSectionHeading(6, "전략 제안"),
                    ...report.strategyProposal.map((item, i) => createPara(`${i + 1}. ${item}`)),

                    // 7. 기대 효과
                    createSectionHeading(7, "기대 효과"),
                    createThreeColTable(report.effectTable),
                ],
            }
        ]
    });

    // 파일 생성 및 다운로드
    Packer.toBlob(doc).then(blob => {
        console.log("Word 문서 생성 완료");
        saveAs(blob, "AI_전략_제안서_초안.docx");
    }).catch(error => {
        console.error("Word 문서 생성 오류:", error);
    });
}


// React 컴포넌트 정의
// 1. 메인 App 컴포넌트
function App() {
    // 상태 정의 (useState)
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

    // 핵심 로직 (이벤트 핸들러)
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

    // 모달 핸들러 (2종류)
    // 1. 패널 모달 열기 / 닫기
    const openPanelModal = (panel) => {
        setSelectedPanel(panel); // 1. 데이터 먼저 삽입 (아직 안 보임)
        setTimeout(() => {
            setIsPanelModalOpen(true); // 2. (20ms 뒤) '열어라' 명령
        }, 20);
    };
    const closePanelModal = () => {
        setIsPanelModalOpen(false); // 1. '닫아라' 명령 (애니메이션 시작)
        setTimeout(() => {
            setSelectedPanel(null); // 2. (300ms 뒤) 데이터 제거 (컴포넌트 소멸)
        }, 300); 
    };

    // 2. 전략 모댤 열기/닫기
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

    // 새 '전체 패널' 닫기 핸들러
    const handleCloseAllPanels = () => {
        setIsAllPanelsExiting(true); // 1. '사라지는 중' 상태로 변경 (CSS 애니메이션 시작)
        setTimeout(() => {
            // 2. (300ms 뒤) 애니메이션이 끝나면 실제 상태 변경
            setIsAllPanelsViewVisible(false);
            setIsAllPanelsExiting(false);
        }, 300); // CSS 애니메이션 시간과 동일하게 설정
    };

    // 뷰 렌더링 로직
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
                  
                <header className="hero-header">
                    <img src="/logo.png" className="logo" alt="App Logo" />
                    
                    {/* "검색 전"에만 보이는 큰 제목/설명 */}
                    <h1>AI로 잠재 고객을 발견하세요</h1>
                    <p>원하는 타겟을 자연어로 검색하고, AI가 제안하는 마케팅/서비스 전략 인사이트를 확인해보세요.</p>
                    
                    {/* "검색 후"에만 보이는 새 제목 */}
                    <h2 className="app-title-active">AI Panel Insight</h2>
                </header>

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
                            autoComplete = "off" // 이전 입력값 안 보이게
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

                                {/* 공통 특성 (단순 인사이트) */}
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

                                {/* AI 추천 전략 */}
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
            
            {/* 모달 렌더링 (2종류) */}
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

// 하위 컴포넌트들
// 2. '전체 패널 보기' 뷰
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

// 3. 패널 상세 모달
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

// 4. '단순 인사이트' 카드 컴포넌트
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


// 5. 'AI 전략' 카드 컴포넌트
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


// 6. 'AI 전략 상세' 모달 컴포넌트
function StrategyDetailModal({ isOpen, onClose, strategy }) {
    const reportData = strategy.report;
    
    const onDownloadClick = () => {
        handleDownloadDocx(reportData);
    };

    return (
        <>
            <div id="modal-overlay" className={`modal-overlay ${isOpen ? 'visible' : ''}`} onClick={onClose}></div>
            
            <div className={`strategy-detail-modal ${isOpen ? 'open' : ''}`}>
                <button id="strategy-modal-close-btn" title="닫기" onClick={onClose}>&times;</button>
                <div className="modal-header">
                    <h3>{reportData?.projectName || "AI 전략 상세 보기"}</h3>
                    <p className="report-subtitle">AI를 활용한 개인 맞춤형 루틴형 건강관리 제안서</p>
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

// 7. 전략 보고서 내용 컴포넌트 (모달 내부)
function StrategyReportContent({ report }) {
    return (
        <div className="report-layout">

            {/* 1. 프로젝트 요약 */}
            <div className="report-section">
                <h3><span>1</span> 프로젝트 요약</h3>
                <table className="report-table">
                    <tbody>
                        <tr>
                            <th>프로젝트명</th>
                            <td>AI 헬스 코치 (가칭)</td>
                        </tr>
                        <tr>
                            <th>타겟 고객</th>
                            <td>수도권 30대 여성 직장인, 스마트워치 사용자, 건강 관심층</td>
                        </tr>
                        <tr>
                            <th>핵심 인사이트</th>
                            <td>'꾸준함' 관련 키워드 사용률 2.3배 증가, 웰니스 소비 1.8배 상승</td>
                        </tr>
                        <tr>
                            <th>핵심 제안</th>
                            <td>AI가 개인의 루틴 데이터를 분석해 지속 가능한 건강 습관을 디자인</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            {/* 2. 문제 정의 */}
            <div className="report-section">
                <h3><span>2</span> 문제 정의</h3>
                <p>
                    바쁜 직장인들은 건강관리의 필요성을 인식하고 있으나, 지속적 실천과 맞춤형 루틴 관리의 부재로 실행률이 낮습니다. 기존 헬스케어 앱은 일시적 사용에 머무르고 있으며, 구독형 루틴 제공 서비스의 시장 공백이 존재합니다.
                </p>
            </div>

            {/* 3. 핵심 가치 */}
            <div className="report-section">
                <h3><span>3</span> 핵심 가치</h3>
                <p className="highlight-text">"꾸준함을 디자인한다"</p>
                <p>
                    데이터 기반 AI 분석으로 개인의 패턴에 최적화된 운동/영양/휴식 루틴을 자동 추천하여 건강한 습관을 형성하게 합니다.
                </p>
            </div>

            {/* 4. 인사이트 근거 */}
            <div className="report-section">
                <h3><span>4</span> 인사이트 근거</h3>
                <table className="report-table">
                    <thead>
                        <tr>
                            <th>지표</th>
                            <th>수치</th>
                            <th>의미</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>스마트워치 보유율</td>
                            <td>64%</td>
                            <td>건강 관련 데이터 수집 기반 확대</td>
                        </tr>
                        <tr>
                            <td>헬스 관련 소비 증가율</td>
                            <td>+1.8배</td>
                            <td>웰니스 산업 성장세 강화</td>
                        </tr>
                        <tr>
                            <td>'꾸준함' 키워드 검색량</td>
                            <td>+2.3배</td>
                            <td>지속 가능한 루틴화 욕구 증가</td>
                        </tr>
                        <tr>
                            <td>'홈트레이닝' 언급량</td>
                            <td>+1.6배</td>
                            <td>집중적 자기관리 트렌드 강화</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            {/* 5. 서비스 개요 */}
            <div className="report-section">
                <h3><span>5</span> 서비스 개요</h3>
                <table className="report-table">
                    <thead>
                        <tr>
                            <th>항목</th>
                            <th>내용</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <th>서비스 형태</th>
                            <td>AI 기반 건강 루틴 구독형 코칭 서비스</td>
                        </tr>
                        <tr>
                            <th>핵심 기능</th>
                            <td>데이터 분석 / 루틴 자동 추천 / AI 피드백</td>
                        </tr>
                        <tr>
                            <th>차별점</th>
                            <td>지속성 중심의 구독 + 개인화 루틴 추천 결합</td>
                        </tr>
                        <tr>
                            <th>구독 모델</th>
                            <td>무료 베이직 / 유료 프리미엄 / 전문가 매칭</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            {/* 6. 전략 제안 */}
            <div className="report-section">
                <h3><span>6</span> 전략 제안</h3>
                <ol className="report-list">
                    <li>스마트워치 연동형 MVP 출시</li>
                    <li>B2B 제휴 (직장인 복지 플랫폼 / 보험사 등)</li>
                    <li>AI 피드백 기능 및 목표 기반 루틴 강화</li>
                </ol>
            </div>

            {/* 7. 기대 효과 */}
            <div className="report-section">
                <h3><span>7</span> 기대 효과</h3>
                <table className="report-table">
                    <thead>
                        <tr>
                            <th>구분</th>
                            <th>정량적 효과</th>
                            <th>정성적 효과</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>사용자</td>
                            <td>앱 유지율 +30%</td>
                            <td>루틴화 및 건강 동기 부여</td>
                        </tr>
                        <tr>
                            <td>기업</td>
                            <td>구독 매출 +15%</td>
                            <td>브랜드 신뢰도 향상</td>
                        </tr>
                        <tr>
                            <td>사회</td>
                            <td>건강 실천율 향상</td>
                            <td>헬스케어 데이터 활성화</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    );
}


// 8. 재사용 컴포넌트들
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