import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';

// docx 및 file-saver 라이브러리
import { 
    Document, Packer, Paragraph, TextRun, HeadingLevel, 
    Table, TableRow, TableCell, WidthType, BorderStyle, AlignmentType 
} from 'docx';
import { saveAs } from 'file-saver';

// API_BASE_URL 추가
const API_BASE_URL = 'http://localhost:8000';

// Word(.docx) 다운로드 생성 함수
async function handleDownloadDocx(report) {
    if (!report) return;

    const titleStyle = {
        children: [
            new TextRun({
                text: report.projectName,
                bold: true,
                size: 48
            })
        ],
        heading: HeadingLevel.TITLE,
        alignment: AlignmentType.CENTER,
    };
    
    const subtitleStyle = {
        text: report.projectSubtitle,
        heading: HeadingLevel.HEADING_1,
        style: "Subtitle", 
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
    };

    const createSectionHeading = (number, text) => {
        return new Paragraph({
            children: [
                new TextRun({ text: `${number} `, size: 32, bold: true }),
                new TextRun({ text: text, size: 32, bold: true }),
            ],
            spacing: { before: 400, after: 200 },
        });
    };

    const createPara = (text) => {
        return new Paragraph({
            children: [new TextRun({ text: text, size: 22 })],
            spacing: { after: 100 },
        });
    };

    const BORDER_STYLE = { style: BorderStyle.SINGLE, size: 1, color: "E0E6ED" };
    const TABLE_BORDERS = { top: BORDER_STYLE, bottom: BORDER_STYLE, left: BORDER_STYLE, right: BORDER_STYLE };

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
                    createSectionHeading(1, "프로젝트 요약"),
                    createTwoColTable(report.summaryTable),
                    createSectionHeading(2, "문제 정의"),
                    createPara(report.problemDefinition),
                    createSectionHeading(3, "핵심 가치"),
                    new Paragraph({
                        children: [new TextRun({ text: report.coreValueHighlight, size: 26, bold: true, color: "14213D" })],
                        spacing: { after: 100 },
                    }),
                    createPara(report.coreValueText),
                    createSectionHeading(4, "인사이트 근거"),
                    createThreeColTable(report.insightTable),
                    createSectionHeading(5, "서비스 개요"),
                    createTwoColTable(report.serviceTable.rows),
                    createSectionHeading(6, "전략 제안"),
                    ...report.strategyProposal.map((item, i) => createPara(`${i + 1}. ${item}`)),
                    createSectionHeading(7, "기대 효과"),
                    createThreeColTable(report.effectTable),
                ],
            }
        ]
    });

    Packer.toBlob(doc).then(blob => {
        console.log("Word 문서 생성 완료");
        saveAs(blob, "AI_전략_제안서_초안.docx");
    }).catch(error => {
        console.error("Word 문서 생성 오류:", error);
    });
}

// React 컴포넌트 정의
function App() {
    const [query, setQuery] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSearched, setIsSearched] = useState(false);
    
    const [filterTags, setFilterTags] = useState([]);
    const [totalCount, setTotalCount] = useState(0);
    const [samplePanels, setSamplePanels] = useState([]);
    const [currentFullPanelList, setCurrentFullPanelList] = useState([]);
    
    const [recommendations, setRecommendations] = useState([]);
    const [strategyCards, setStrategyCards] = useState([]);
    
    const [isPanelModalOpen, setIsPanelModalOpen] = useState(false);
    const [selectedPanel, setSelectedPanel] = useState(null);
    const [isStrategyModalOpen, setIsStrategyModalOpen] = useState(false);
    const [selectedStrategy, setSelectedStrategy] = useState(null);

    const [isAllPanelsViewVisible, setIsAllPanelsViewVisible] = useState(false);
    const [isAllPanelsExiting, setIsAllPanelsExiting] = useState(false);

    const clearResults = () => {
        setIsSearched(false);
        setFilterTags([]);
        setTotalCount(0);
        setSamplePanels([]);
        setRecommendations([]);
        setStrategyCards([]);
        setCurrentFullPanelList([]);
    };

    const handleSearch = async (queryToSearch) => {
        if (!queryToSearch && filterTags.length === 0) {
            if (queryToSearch === "") clearResults();
            return;
        }
        setIsLoading(true);
        setIsSearched(true); 
        console.log(`[프론트] 백엔드로 전송할 쿼리: "${queryToSearch}"`);

        try {
            const response = await axios.post(`${API_BASE_URL}/api/v1/search`, {
                query: queryToSearch 
            });

            const apiResponse = response.data;

            console.log('🔍 백엔드 전체 응답:', JSON.stringify(apiResponse, null, 2));
            console.log('🔍 samplePanels 첫번째:', apiResponse.samplePanels[0]);
            
            // ✅ 즉시 갱신 (React 배치 업데이트 방지)
            setTotalCount(apiResponse.totalCount);
            setFilterTags(apiResponse.filterTags || []);
            setSamplePanels(apiResponse.samplePanels);
            setCurrentFullPanelList(apiResponse.currentFullPanelList);
            setRecommendations(apiResponse.recommendations);
            setStrategyCards(apiResponse.strategyCards || []);
            
            // 강제 리렌더링 트리거
            setTimeout(() => {
                console.log('✅ 통계 갱신 완료:', apiResponse.totalCount);
            }, 0);

            // ✅ 자동 로딩: preloadHint가 있으면 백그라운드 생성
            const preloadStrategy = (apiResponse.strategyCards || []).find(s => s.preloadHint);
            if (preloadStrategy) {
                console.log('🔄 전략 사전 생성 시작...');
                axios.post(`${API_BASE_URL}/api/v1/generate-report`, {
                    strategyId: preloadStrategy.id,
                    strategyName: preloadStrategy.strategyName,
                    coreTarget: preloadStrategy.coreTarget,
                    originalQuery: queryToSearch
                }).then(() => {
                    console.log('✅ 전략 사전 생성 완료 (캐싱됨)');
                }).catch(err => {
                    console.log('⚠️ 사전 생성 실패 (무시):', err.message);
                });
            }

            } catch (error) {
            console.error("API 호출 중 오류 발생:", error);
            clearResults();
        
        } finally {
            setIsLoading(false);
        }
    };
    
    const handleRecommendationClick = (rec) => {
        const actionData = rec.action.data;
        const partToAdd = actionData.queryPart || actionData.value;
        
        // 빈 문자열이면 무시 (조건 제거 케이스)
        if (!partToAdd || partToAdd.trim() === '') {
            console.log('조건 제거 제안 - 검색어 변경 없음');
            return;
        }
        
        // ✅ 개선된 중복 체크 (단어 단위)
        const queryLower = query.toLowerCase().trim();
        const partLower = partToAdd.toLowerCase().trim();
        
        // 정확한 단어 매칭
        const queryWords = queryLower.split(/[,\s]+/).filter(w => w);
        const isAlreadyIncluded = queryWords.some(word => 
            word === partLower || 
            partLower.includes(word) || 
            word.includes(partLower)
        );
        
        if (isAlreadyIncluded) {
            console.log(`이미 포함된 조건: "${partToAdd}"`);
            return;
        }
        
        // 쿼리 추가
        const newQuery = query.trim() 
            ? `${query.trim()}, ${partToAdd}` 
            : partToAdd;
        
        setQuery(newQuery);
        handleSearch(newQuery);
    };
    
    const handleTagRemove = (tagToRemove) => {
        console.log('🗑️ 태그 삭제:', tagToRemove);
        
        const regex = new RegExp(`\\s*,?\\s*${tagToRemove.queryPart}\\s*,?`, 'i');
        const newQuery = query.replace(regex, ',').replace(/^,|,$/g, '').replace(/, *,/g, ', ');
        const newQueryTrimmed = newQuery.trim();
        
        // 즉시 state 업데이트
        setQuery(newQueryTrimmed);
        setFilterTags(prev => prev.filter(tag => tag.id !== tagToRemove.id));
        
        // 즉시 검색 실행
        handleSearch(newQueryTrimmed);
    };

    const openPanelModal = (panel) => {
        setSelectedPanel(panel);
        setTimeout(() => {
            setIsPanelModalOpen(true);
        }, 20);
    };
    
    const closePanelModal = () => {
        setIsPanelModalOpen(false);
        setTimeout(() => {
            setSelectedPanel(null);
        }, 300); 
    };

    const openStrategyModal = (strategy) => {
        setSelectedStrategy(strategy);
        setTimeout(() => {
            setIsStrategyModalOpen(true);
        }, 20);
    };
    
    const closeStrategyModal = () => {
        setIsStrategyModalOpen(false);
        setTimeout(() => {
            setSelectedStrategy(null);
        }, 300);
    };

    const handleCloseAllPanels = () => {
        setIsAllPanelsExiting(true);
        setTimeout(() => {
            setIsAllPanelsViewVisible(false);
            setIsAllPanelsExiting(false);
        }, 300);
    };

    if (isAllPanelsViewVisible || isAllPanelsExiting) {
        return (
            <AllPanelsView
                fullPanelList={currentFullPanelList}
                totalCount={totalCount}
                onBack={handleCloseAllPanels}
                isExiting={isAllPanelsExiting}
            />
        );
    }

    return (
        <>
            <div className={`container ${isSearched ? 'search-active' : ''}`}>
                <header className="hero-header">
                    <img src="/logo.png" className="logo" alt="App Logo" />
                    <h1>AI로 잠재 고객을 발견하세요</h1>
                    <p>원하는 타겟을 자연어로 검색하고, AI가 제안하는 마케팅/서비스 전략 인사이트를 확인해보세요.</p>
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
                            autoComplete="off"
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

                {isLoading && <Loader />}

                {isSearched && !isLoading && totalCount > 0 && (
                    <div id="results-wrapper" className="visible">
                        {(recommendations.length > 0 || strategyCards.length > 0) && (
                            <section id="discovery-zone" className="workspace-section">
                                <h2>추천 인사이트</h2>
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
                    query={query}  
                />
            )}
        </>
    );
}

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

function RecommendationCard({ rec, onClick }) {
    const actionData = rec.action?.data || {};
    const queryPart = actionData.queryPart || actionData.value || '';
    
    // 툴팁 텍스트 생성
    const tooltipText = queryPart.trim() 
        ? `"${queryPart}" 조건을 검색어에 추가합니다`
        : '조건을 변경합니다';
    
    return (
        <div className="recommendation-card">
            <p>{rec.text}</p>
            <button 
                onClick={() => onClick(rec)}
                title={tooltipText}
            >
                {rec.action.buttonText}
            </button>
        </div>
    );
}

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

function StrategyDetailModal({ isOpen, onClose, strategy, query }) {
    const [reportData, setReportData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    
    useEffect(() => {
        if (isOpen && strategy) {
            setReportData(null);
            setIsLoading(true);
            
            axios.post(`${API_BASE_URL}/api/v1/generate-report`, {
                strategyId: strategy.id,
                strategyName: strategy.strategyName,
                coreTarget: strategy.coreTarget,
                originalQuery: query
            })
            .then(response => {
                setReportData(response.data.report);
            })
            .catch(error => {
                console.error("리포트 로딩 실패:", error);
            })
            .finally(() => {
                setIsLoading(false);
            });
        }
    }, [isOpen, strategy, query]);

    
    const onDownloadClick = () => {
        handleDownloadDocx(reportData);
    };

    return (
        <>
            <div className={`modal-overlay ${isOpen ? 'visible' : ''}`} onClick={onClose}></div>
            
            <div className={`strategy-detail-modal ${isOpen ? 'open' : ''}`}>
                <button id="strategy-modal-close-btn" title="닫기" onClick={onClose}>&times;</button>
                <div className="modal-header">
                    <h3>{strategy?.strategyName || ''}</h3>
                    <p className="report-subtitle">{reportData?.projectSubtitle || ''}</p>
                </div>
                <div className="strategy-modal-content">
                    {isLoading ? (
                        <div style={{ textAlign: 'center', padding: '50px' }}>
                            <Loader />
                            <p>AI가 전략 리포트를 생성하고 있습니다...</p>
                            <p style={{ fontSize: '0.9em', color: '#666' }}>
                                (약 10-20초 소요)
                            </p>
                        </div>
                    ) : reportData ? (
                        <StrategyReportContent report={reportData} />
                    ) : (
                        <p>리포트를 불러올 수 없습니다. 다시 시도해주세요.</p>
                    )}
                </div>
                <div className="strategy-modal-footer">
                    <button 
                        className="download-btn" 
                        onClick={onDownloadClick} 
                        disabled={!reportData || isLoading}
                    >
                        📄 기획서 초안 (Word) 다운로드
                    </button>
                </div>
            </div>
        </>
    );
}

function StrategyReportContent({ report }) {
    if (!report) {
        return <p>전략 데이터를 불러오는 중입니다...</p>;
    }

    return (
        <div className="report-layout">
            <div className="report-section">
                <h3><span>1</span> 프로젝트 요약</h3>
                <table className="report-table">
                    <tbody>
                        {report.summaryTable && report.summaryTable.map((item, index) => (
                            <tr key={index}>
                                <th>{item.th}</th>
                                <td>{item.td}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            
            <div className="report-section">
                <h3><span>2</span> 문제 정의</h3>
                <p>{report.problemDefinition}</p>
            </div>
            
            <div className="report-section">
                <h3><span>3</span> 핵심 가치</h3>
                <p className="highlight-text">"{report.coreValueHighlight}"</p>
                <p>{report.coreValueText}</p>
            </div>
            
            <div className="report-section">
                <h3><span>4</span> 인사이트 근거</h3>
                {report.insightTable?.headers ? (
                    <table className="report-table">
                        <thead>
                            <tr>
                                {report.insightTable.headers.map((header, i) => <th key={i}>{header}</th>)}
                            </tr>
                        </thead>
                        <tbody>
                            {report.insightTable.rows.map((row, i) => (
                                <tr key={i}>
                                    {Array.isArray(row) ? (
                                        row.map((cell, j) => <td key={j}>{cell}</td>)
                                    ) : (
                                        <>
                                            <td>{row['지표']}</td>
                                            <td>{row['수치']}</td>
                                            <td>{row['의미']}</td>
                                        </>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                ) : (
                    <p>인사이트 데이터를 생성 중입니다...</p>
                )}
            </div>
            
            <div className="report-section">
                <h3><span>5</span> 서비스 개요</h3>
                <table className="report-table">
                    <tbody>
                        {report.serviceTable.rows && report.serviceTable.rows.map((row, index) => (
                            <tr key={index}>
                                {/* ✅ 객체/배열 모두 지원 */}
                                <th>{row.th || row[0]}</th>
                                <td>{row.td || row[1]}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            
            <div className="report-section">
                <h3><span>6</span> 전략 제안</h3>
                <ol className="report-list">
                    {report.strategyProposal.map((item, i) => (
                        <li key={i}>{item}</li>
                    ))}
                </ol>
            </div>
            
            <div className="report-section">
                <h3><span>7</span> 기대 효과</h3>
                {report.effectTable?.headers ? (
                    <table className="report-table">
                        <thead>
                            <tr>
                                {report.effectTable.headers.map((header, i) => <th key={i}>{header}</th>)}
                            </tr>
                        </thead>
                        <tbody>
                            {report.effectTable.rows.map((row, i) => (
                                <tr key={i}>
                                    {Array.isArray(row) ? (
                                        row.map((cell, j) => <td key={j}>{cell}</td>)
                                    ) : (
                                        <>
                                            <td>{row['구분']}</td>
                                            <td>{row['정량적 효과']}</td>
                                            <td>{row['정성적 효과']}</td>
                                        </>
                                    )}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                ) : (
                    <p>기대 효과를 분석 중입니다...</p>
                )}
            </div>
        </div>
    );
}

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
                <span>{panel.panel_id || panel.panel_uuid}</span>
                <button className="detail-btn" onClick={() => onDetailClick(panel)}>자세히 보기</button>
            </h4>
            <ul>
                <li><strong>나이:</strong> {2025 - (panel.birth_year || 2000)}세</li>
                <li><strong>성별:</strong> {panel.gender || '미기재'}</li>
                <li><strong>지역:</strong> {panel.region_main ? `${panel.region_main} ${panel.region_sub || ''}` : '미기재'}</li>
                <li><strong>직업:</strong> {panel.job_category || '미기재'}</li>
            </ul>
        </div>
    );
}

const PanelDetail = ({ panel, onClose }) => {
  const [detailData, setDetailData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchDetail = async () => {
      try {
        setLoading(true);
        const response = await fetch(`http://localhost:8000/api/v1/panel/${panel.panel_uuid}`);
        const result = await response.json();

        if (result.success) {
          setDetailData(result.data);
        }
      } catch (error) {
        console.error('패널 상세 정보 로드 실패:', error);
      } finally {
        setLoading(false);
      }
    };

    if (panel?.panel_uuid) {
      fetchDetail();
    }
  }, [panel]);

  if (!panel) return null;

  return (
    <div className="panel-detail-overlay" onClick={onClose}>
      <div className="panel-detail-modal" onClick={(e) => e.stopPropagation()}>
        
        <div className="detail-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '10px' }}>
            
            <div className="profile-avatar">P</div>
            
            <div className="header-info">
               {/* 이름 옆/아래 여백 제거를 위해 margin 조절 */}
              <h2 style={{ margin: '0 0 5px 0' }}>{panel.panel_id || panel.panel_uuid}</h2>
              <p className="detail-subtitle" style={{ margin: 0 }}>
                {panel.gender || '성별 미상'}, {2025 - (panel.birth_year || 2000)}세
              </p>
            </div>

          </div>
          
          {/* 나머지 정보는 아래에 배치 */}
          <br></br>
          <p className="detail-location" style={{ marginTop: '10px' }}>
            거주지: {panel.region_main ? `${panel.region_main} ${panel.region_sub || ''}` : '거주지 정보 없음'}
          </p>
          <p className="detail-job">
            직업: {panel.job_category || '직업 정보 없음'}
          </p>
          <br></br>
        </div>

        {loading ? (
          <div className="loading-spinner">로딩 중...</div>
        ) : (
          <div className="detail-content">
            <div className="detail-section">
              <h3>상세 정보</h3>
              
              {detailData?.grouped_details && Object.keys(detailData.grouped_details).length > 0 ? (
                Object.entries(detailData.grouped_details).map(([category, items]) => (
                  <div key={category} className="info-category">
                    <h4>{category}</h4>
                    <div className="info-grid">
                      {items.map((item, index) => (
                        <div key={index} className="info-row">
                          <span className="info-label">{item.label}:</span>
                          <span className="info-value">{item.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <p>상세 정보가 없습니다.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
  
};

function Loader() {
    return <div id="loader" style={{ display: 'block' }}></div>;
}

export default App;