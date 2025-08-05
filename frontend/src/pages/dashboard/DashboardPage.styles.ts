import { createUseStyles } from 'react-jss';

export const DashboardPageStyles = createUseStyles({
  container: {
    display: 'flex',
    flexDirection: 'column',
    width: '100%',
    height: '100%',
    boxSizing: 'border-box',
    overflow: 'hidden',
    '@media (max-width:1000px)': {
      marginTop: 60
    }
  },
  headerSection: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '24px 32px',
    backgroundColor: 'white',
    borderBottom: '1px solid #e0e0e0',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
    '@media (max-width:1000px)': {
      padding: '16px'
    }
  },
  backgroundLogo: {
    height: 60,
    width: 'auto',
    marginBottom: 16,
    '@media (max-width:1000px)': {
      height: 40
    }
  },
  title: {
    fontSize: 20,
    fontWeight: 600,
    color: '#181a25',
    textAlign: 'center',
    margin: '0 0 8px 0',
    '@media (max-width:1000px)': {
      fontSize: 16
    }
  },
  exp: {
    fontSize: 14,
    color: '#55565d',
    textAlign: 'center',
    margin: 0,
    maxWidth: 800,
    lineHeight: 1.5,
    '@media (max-width:1000px)': {
      fontSize: 12
    }
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
    '@media (max-width:1000px)': {
      flexDirection: 'column'
    }
  },
  leftPanel: {
    width: '40%',
    minWidth: 400,
    maxWidth: 600,
    backgroundColor: '#f8f9fa',
    borderRight: '1px solid #e0e0e0',
    overflow: 'auto',
    padding: 24,
    boxSizing: 'border-box',
    '@media (max-width:1000px)': {
      width: '100%',
      minWidth: 'unset',
      maxWidth: 'unset',
      borderRight: 'none',
      borderBottom: '1px solid #e0e0e0',
      padding: 16,
      maxHeight: '50vh'
    }
  },
  rightPanel: {
    flex: 1,
    backgroundColor: 'white',
    overflow: 'auto',
    padding: 24,
    boxSizing: 'border-box',
    '@media (max-width:1000px)': {
      padding: 16,
      minHeight: '50vh'
    }
  },
  panelHeader: {
    marginBottom: 24,
    '& h3': {
      fontSize: 18,
      fontWeight: 600,
      color: '#181a25',
      margin: '0 0 8px 0'
    },
    '& p': {
      fontSize: 14,
      color: '#55565d',
      margin: 0
    },
    '@media (max-width:1000px)': {
      marginBottom: 16,
      '& h3': {
        fontSize: 16
      },
      '& p': {
        fontSize: 12
      }
    }
  },
  dropzone: {
    border: '2px dashed #d0d0d0',
    borderRadius: 12,
    padding: 32,
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    backgroundColor: 'white',
    marginBottom: 16,
    '&:hover': {
      borderColor: '#195cd7',
      backgroundColor: '#f0f7ff'
    },
    '@media (max-width:1000px)': {
      padding: 24
    }
  },
  dropzoneActive: {
    borderColor: '#195cd7',
    backgroundColor: '#e6f2ff',
    transform: 'scale(1.02)'
  },
  dropzoneContent: {
    pointerEvents: 'none'
  },
  dropzoneIcon: {
    fontSize: 48,
    marginBottom: 16,
    display: 'block'
  },
  dropzoneText: {
    fontSize: 16,
    fontWeight: 500,
    color: '#181a25',
    marginBottom: 8,
    '@media (max-width:1000px)': {
      fontSize: 14
    }
  },
  dropzoneSubtext: {
    fontSize: 14,
    color: '#55565d',
    '@media (max-width:1000px)': {
      fontSize: 12
    }
  },
  dropzoneFileCount: {
    fontSize: 14,
    color: '#195cd7',
    fontWeight: 500,
    marginTop: 16,
    padding: '8px 16px',
    backgroundColor: '#e6f2ff',
    borderRadius: 20,
    display: 'inline-block'
  },
  matchInfo: {
    marginBottom: 16,
    padding: 12,
    backgroundColor: '#e8f5e8',
    borderRadius: 8,
    border: '1px solid #4caf50'
  },
  matchInfoContent: {
    fontSize: 14,
    color: '#2e7d32',
    '& ul': {
      margin: '8px 0 0 20px',
      fontSize: 12,
      '& li': {
        marginBottom: 4
      }
    },
    '@media (max-width:1000px)': {
      fontSize: 12,
      '& ul': {
        fontSize: 11
      }
    }
  },
  uploadButton: {
    width: '100%',
    padding: 12,
    fontSize: 16,
    fontWeight: 500,
    color: 'white',
    backgroundColor: '#195cd7',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'background 0.3s',
    marginBottom: 16,
    '&:hover': {
      backgroundColor: '#1c67f0'
    },
    '&:active': {
      backgroundColor: '#174bb5'
    },
    '&:disabled': {
      backgroundColor: '#cccccc',
      cursor: 'not-allowed'
    },
    '@media (max-width:1000px)': {
      fontSize: 14,
      padding: 10
    }
  },
  processingInfo: {
    fontSize: 14,
    color: '#55565d',
    textAlign: 'center',
    marginBottom: 16,
    '@media (max-width:1000px)': {
      fontSize: 12
    }
  },
  fileListSection: {
    maxHeight: 'calc(100vh - 600px)',
    overflow: 'auto',
    marginBottom: 24,
    '@media (max-width:1000px)': {
      maxHeight: 200
    }
  },
  uploadedItem: {
    width: '100%',
    backgroundColor: 'white',
    borderRadius: 8,
    border: '1px solid #e0e0e0',
    padding: 16,
    marginBottom: 12,
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    transition: 'box-shadow 0.2s',
    '&:hover': {
      boxShadow: '0 2px 6px rgba(0,0,0,0.1)'
    },
    '@media (max-width:1000px)': {
      padding: 12
    }
  },
  uploadedItemFirstSection: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12
  },
  uploadedItemStatus: {
    display: 'flex',
    alignItems: 'center',
    padding: '4px 12px',
    borderRadius: 16,
    fontSize: 12,
    fontWeight: 500,
    '&.green': {
      backgroundColor: '#e8f5e8',
      color: '#2e7d32'
    },
    '&.yellow': {
      backgroundColor: '#fff8e1',
      color: '#f57c00'
    },
    '&.red': {
      backgroundColor: '#ffebee',
      color: '#c62828'
    },
    '&.blue': {
      backgroundColor: '#e3f2fd',
      color: '#1565c0'
    }
  },
  uploadedItemStatusText: {
    margin: 0
  },
  progressContainer: {
    width: '100%',
    height: '1rem',
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 8
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#195cd7',
    transition: 'width 0.3s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  progressText: {
    fontSize: 10,
    color: 'white',
    fontWeight: 500
  },
  excelOperations: {
    marginTop: 24,
    paddingTop: 24,
    borderTop: '2px solid #e0e0e0'
  },
  exportSection: {
    marginBottom: 24,
    '& h4': {
      fontSize: 16,
      fontWeight: 600,
      color: '#181a25',
      marginBottom: 12
    }
  },
  exportButton: {
    width: '100%',
    padding: 12,
    fontSize: 14,
    fontWeight: 500,
    color: 'white',
    backgroundColor: '#10b86b',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'background 0.3s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    '&:hover': {
      backgroundColor: '#0ea760'
    },
    '&:disabled': {
      backgroundColor: '#cccccc',
      cursor: 'not-allowed'
    },
    '& img': {
      width: 16,
      height: 16
    }
  },
  exportProgress: {
    marginBottom: 12,
    height: 20,
    backgroundColor: '#e0e0e0',
    borderRadius: 10,
    overflow: 'hidden'
  },
  exportProgressBar: {
    height: '100%',
    backgroundColor: '#10b86b',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: 12,
    fontWeight: 500,
    transition: 'width 0.3s'
  },
  mergeSection: {
    '& h4': {
      fontSize: 16,
      fontWeight: 600,
      color: '#181a25',
      marginBottom: 12
    }
  },
  excelFileSelection: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
    padding: 8,
    backgroundColor: 'white',
    border: '1px solid #e0e0e0',
    borderRadius: 8
  },
  excelSelectButton: {
    padding: '6px 12px',
    fontSize: 14,
    fontWeight: 500,
    color: '#181a25',
    backgroundColor: '#f0f0f0',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    transition: 'background 0.2s',
    '&:hover': {
      backgroundColor: '#e0e0e0'
    },
    '&:disabled': {
      opacity: 0.5,
      cursor: 'not-allowed'
    }
  },
  excelFileName: {
    flex: 1,
    fontSize: 14,
    color: '#55565d',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },
  removeExcelButton: {
    padding: '4px 8px',
    fontSize: 12,
    color: '#dc3545',
    backgroundColor: 'transparent',
    border: '1px solid #dc3545',
    borderRadius: 4,
    cursor: 'pointer',
    transition: 'all 0.2s',
    '&:hover': {
      backgroundColor: '#dc3545',
      color: 'white'
    },
    '&:disabled': {
      opacity: 0.5,
      cursor: 'not-allowed'
    }
  },
  mergeButton: {
    width: '100%',
    padding: 12,
    fontSize: 14,
    fontWeight: 500,
    color: 'white',
    backgroundColor: '#ffbf0a',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'background 0.3s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    '&:hover': {
      backgroundColor: '#e6ab00'
    },
    '&:disabled': {
      backgroundColor: '#cccccc',
      cursor: 'not-allowed'
    },
    '& img': {
      width: 16,
      height: 16
    }
  },
  mergeProgress: {
    marginBottom: 12,
    height: 20,
    backgroundColor: '#e0e0e0',
    borderRadius: 10,
    overflow: 'hidden'
  },
  mergeProgressBar: {
    height: '100%',
    backgroundColor: '#ffbf0a',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: 12,
    fontWeight: 500,
    transition: 'width 0.3s'
  },
  resultsSection: {
    height: 'calc(100vh - 280px)',
    overflow: 'auto',
    '@media (max-width:1000px)': {
      height: 'auto',
      minHeight: 300
    }
  },
  emptyResults: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    minHeight: 400,
    color: '#999'
  },
  emptyIcon: {
    fontSize: 64,
    marginBottom: 16,
    opacity: 0.5
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    marginTop: 8,
    maxWidth: 300
  },
  analyseItem: {
    width: '100%',
    backgroundColor: 'white',
    borderRadius: 8,
    border: '1px solid #e0e0e0',
    marginBottom: 16,
    overflow: 'hidden',
    transition: 'all 0.3s',
    '&:hover': {
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
    },
    '&.active': {
      border: '1px solid #195cd7',
      boxShadow: '0 4px 12px rgba(25,92,215,0.15)'
    }
  },
  analyseFirstSection: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 20,
    cursor: 'pointer',
    transition: 'background 0.2s',
    '&:hover': {
      backgroundColor: '#f8f9fa'
    },
    '@media (max-width:1000px)': {
      padding: 16
    }
  },
  analyseItemInsideDiv: {
    padding: 20,
    backgroundColor: '#f8f9fa',
    borderTop: '1px solid #e0e0e0',
    '& [class*=analyseItemInsideDiv]': {
      padding: '1rem 0'
    },
    '@media (max-width:1000px)': {
      padding: 16
    }
  },
  analyseFirstDiv: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 32,
    marginBottom: 24,
    '@media (max-width:1000px)': {
      flexDirection: 'column',
      gap: 24
    }
  },
  analyseAlias: {
    fontSize: 16,
    fontWeight: 600,
    color: '#181a25',
    backgroundColor: '#195cd720',
    padding: '12px 20px',
    borderRadius: 8,
    margin: 0,
    whiteSpace: 'nowrap',
    '@media (max-width:1000px)': {
      fontSize: 14,
      padding: '10px 16px'
    }
  },
  modelDiv: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 12
  },
  modelSection: {
    width: 200,
    height: 200,
    backgroundColor: 'white',
    border: '1px solid #e0e0e0',
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
  },
  modelImage: {
    width: '100%',
    height: '100%',
    objectFit: 'contain'
  },
  modelShowButton: {
    padding: '10px 24px',
    fontSize: 14,
    fontWeight: 500,
    color: '#195cd7',
    backgroundColor: '#195cd720',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 0.2s',
    '&:hover': {
      backgroundColor: '#195cd730',
      transform: 'translateY(-1px)'
    }
  },
  line: {
    width: '100%',
    height: 1,
    backgroundColor: '#e0e0e0',
    margin: '24px 0'
  },
  titleSmall: {
    fontSize: 16,
    fontWeight: 600,
    color: '#181a25',
    margin: '0 0 16px 0',
    '@media (max-width:1000px)': {
      fontSize: 14
    }
  },
  analyseSubtitleDiv: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: 12,
    backgroundColor: '#195cd710',
    borderRadius: 8,
    marginBottom: 16,
    '& span': {
      fontSize: 20
    },
    '& p': {
      margin: 0,
      fontSize: 16,
      fontWeight: 500,
      color: '#181a25'
    },
    '@media (max-width:1000px)': {
      '& p': {
        fontSize: 14
      }
    }
  },
  analyseInsideItem: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    alignItems: 'center',
    padding: '12px 16px',
    backgroundColor: 'white',
    borderRadius: 6,
    marginBottom: 8,
    '&:last-child': {
      marginBottom: 0
    }
  },
  analyseItemTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#181a25',
    margin: 0
  },
  analyseItemExp: {
    fontSize: 14,
    fontWeight: 400,
    color: '#55565d',
    margin: 0,
    textAlign: 'right'
  },
  lineAnalyseItem: {
    display: 'none'
  },
  dimensionTable: {
    width: '100%',
    backgroundColor: 'white',
    borderRadius: 8,
    overflow: 'hidden',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
  },
  tableHeader: {
    display: 'flex',
    backgroundColor: '#f5f5f5',
    fontWeight: 600,
    fontSize: 14,
    color: '#181a25'
  },
  tableRow: {
    display: 'flex',
    backgroundColor: 'white',
    borderTop: '1px solid #e0e0e0',
    '&:hover': {
      backgroundColor: '#f8f9fa'
    }
  },
  tableCell: {
    flex: 1,
    padding: '12px 16px',
    textAlign: 'center',
    fontSize: 14,
    color: '#55565d',
    borderRight: '1px solid #e0e0e0',
    '&:last-child': {
      borderRight: 'none'
    }
  },
  analyseMaterialDiv: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 16,
    padding: 16,
    backgroundColor: '#195cd710',
    borderRadius: 8,
    marginBottom: 8,
    '@media (max-width:1000px)': {
      overflowX: 'auto',
      display: 'flex',
      gap: 24
    }
  },
  materialTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#181a25',
    margin: 0,
    whiteSpace: 'nowrap'
  },
  analyseMaterialExpDiv: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 16,
    padding: '12px 16px',
    backgroundColor: 'white',
    borderRadius: 6,
    marginBottom: 8,
    '@media (max-width:1000px)': {
      overflowX: 'auto',
      display: 'flex',
      gap: 24
    }
  },
  materialExp: {
    fontSize: 14,
    color: '#55565d',
    margin: 0,
    whiteSpace: 'nowrap'
  },
  hiddenFileInput: {
    display: 'none'
  },
  retryButton: {
    padding: '4px 12px',
    fontSize: 12,
    fontWeight: 500,
    color: 'white',
    backgroundColor: '#dc3545',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    transition: 'background 0.2s',
    '&:hover': {
      backgroundColor: '#c82333'
    },
    '&:disabled': {
      opacity: 0.5,
      cursor: 'not-allowed'
    }
  }
});
