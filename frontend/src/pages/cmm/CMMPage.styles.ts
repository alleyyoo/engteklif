import { createUseStyles } from 'react-jss';

export const CMMPageStyles = createUseStyles({
  container: {
    display: 'flex',
    flexDirection: 'column',
    width: '100%',
    height: '100%',
    boxSizing: 'border-box',
    overflow: 'hidden',
    backgroundColor: '#f5f6fa',
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

  pageTitle: {
    fontSize: 24,
    fontWeight: 600,
    color: '#181a25',
    margin: '0 0 8px 0',
    '@media (max-width:1000px)': {
      fontSize: 20
    }
  },

  pageDescription: {
    fontSize: 14,
    color: '#55565d',
    textAlign: 'center',
    margin: '0 0 20px 0',
    maxWidth: 600,
    lineHeight: 1.5,
    '@media (max-width:1000px)': {
      fontSize: 12,
      marginBottom: 16
    }
  },

  statsContainer: {
    display: 'flex',
    gap: 16,
    flexWrap: 'wrap',
    justifyContent: 'center',
    '@media (max-width:768px)': {
      gap: 12
    }
  },

  statsCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '16px 24px',
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    border: '1px solid #e0e0e0',
    minWidth: 120,
    transition: 'all 0.3s ease',
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
    },
    '@media (max-width:768px)': {
      padding: '12px 16px',
      minWidth: 100
    }
  },

  statNumber: {
    fontSize: 28,
    fontWeight: 700,
    color: '#195cd7',
    marginBottom: 4,
    '@media (max-width:768px)': {
      fontSize: 24
    }
  },

  statLabel: {
    fontSize: 12,
    color: '#55565d',
    textAlign: 'center',
    whiteSpace: 'nowrap'
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
    maxWidth: 500,
    backgroundColor: 'white',
    borderRight: '1px solid #e0e0e0',
    padding: 24,
    paddingLeft: 0,
    overflow: 'auto',
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
    backgroundColor: '#f8f9fa',
    padding: 24,
    overflow: 'auto',
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
    padding: 40,
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    backgroundColor: '#f8f9fa',
    marginBottom: 20,
    '&:hover': {
      borderColor: '#195cd7',
      backgroundColor: '#f0f7ff'
    },
    '@media (max-width:1000px)': {
      padding: 32
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
    display: 'block',
    opacity: 0.7
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

  fileList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    marginBottom: 16
  },

  fileItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    border: '1px solid #e0e0e0',
    transition: 'all 0.2s',
    '&:hover': {
      backgroundColor: '#f0f1f5',
      borderColor: '#d0d0d0'
    }
  },

  fileInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    flex: 1,
    overflow: 'hidden'
  },

  fileIcon: {
    fontSize: 24,
    flexShrink: 0
  },

  fileDetails: {
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden'
  },

  fileName: {
    fontSize: 14,
    fontWeight: 500,
    color: '#181a25',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap'
  },

  fileSize: {
    fontSize: 12,
    color: '#55565d',
    marginTop: 2
  },

  removeFileButton: {
    width: 24,
    height: 24,
    borderRadius: 4,
    border: '1px solid #dc3545',
    backgroundColor: 'transparent',
    color: '#dc3545',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 'bold',
    transition: 'all 0.2s',
    flexShrink: 0,
    '&:hover': {
      backgroundColor: '#dc3545',
      color: 'white'
    }
  },

  clearButton: {
    width: '100%',
    padding: '8px 16px',
    fontSize: 14,
    fontWeight: 500,
    color: '#6c757d',
    backgroundColor: 'transparent',
    border: '1px solid #6c757d',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 0.2s',
    marginBottom: 16,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    '&:hover': {
      backgroundColor: '#6c757d',
      color: 'white'
    }
  },

  progressSection: {
    marginBottom: 16
  },

  progressBar: {
    width: '100%',
    height: 24,
    backgroundColor: '#e0e0e0',
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: 8
  },

  progressFill: {
    height: '100%',
    backgroundColor: '#195cd7',
    transition: 'width 0.3s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontSize: 12,
    fontWeight: 500
  },

  progressText: {
    fontSize: 12,
    color: '#55565d',
    textAlign: 'center'
  },

  uploadButton: {
    width: '100%',
    padding: 14,
    fontSize: 16,
    fontWeight: 500,
    color: 'white',
    backgroundColor: '#10b86b',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 0.3s',
    marginBottom: 24,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    '&:hover': {
      backgroundColor: '#0ea760',
      transform: 'translateY(-1px)',
      boxShadow: '0 4px 12px rgba(16, 184, 107, 0.3)'
    },
    '&:active': {
      transform: 'translateY(0)'
    },
    '&:disabled': {
      backgroundColor: '#cccccc',
      cursor: 'not-allowed',
      transform: 'none'
    },
    '@media (max-width:1000px)': {
      fontSize: 14,
      padding: 12
    }
  },

  featuresPanel: {
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    padding: 20,
    border: '1px solid #e0e0e0',
    '& h4': {
      fontSize: 16,
      fontWeight: 600,
      color: '#181a25',
      margin: '0 0 12px 0'
    }
  },

  featureList: {
    margin: 0,
    paddingLeft: 20,
    '& li': {
      fontSize: 13,
      color: '#55565d',
      marginBottom: 8,
      lineHeight: 1.5,
      '&:last-child': {
        marginBottom: 0
      }
    }
  },

  analysisSection: {
    height: 'calc(100vh - 280px)',
    '@media (max-width:1000px)': {
      height: 'auto',
      minHeight: 400
    }
  },

  loadingState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#999'
  },

  emptyState: {
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

  analysisGrid: {},

  analysisCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    border: '1px solid #e0e0e0',
    overflow: 'hidden',
    transition: 'all 0.3s',
    '&:hover': {
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      transform: 'translateY(-2px)'
    }
  },

  analysisHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#f8f9fa',
    borderBottom: '1px solid #e0e0e0'
  },

  analysisId: {
    fontSize: 14,
    fontWeight: 600,
    color: '#181a25'
  },

  analysisStats: {
    display: 'flex',
    gap: 8
  },

  analysisBody: {
    padding: 16
  },

  analysisInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    marginBottom: 16
  },

  infoItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8
  },

  infoLabel: {
    fontSize: 13,
    color: '#55565d',
    fontWeight: 500,
    minWidth: 80
  },

  infoValue: {
    fontSize: 13,
    color: '#181a25'
  },

  operationBadges: {
    display: 'flex',
    gap: 4,
    flexWrap: 'wrap'
  },

  badgeContainer: {
    display: 'flex',
    gap: 4,
    flexWrap: 'wrap'
  },

  analysisActions: {
    display: 'flex',
    gap: 8,
    paddingTop: 12,
    borderTop: '1px solid #f0f0f0'
  },

  actionButton: {
    padding: '8px 16px',
    fontSize: 13,
    fontWeight: 500,
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    '&:disabled': {
      opacity: 0.5,
      cursor: 'not-allowed'
    }
  },

  downloadButton: {
    flex: 1,
    color: 'white',
    backgroundColor: '#10b86b',
    '&:hover:not(:disabled)': {
      backgroundColor: '#0ea760'
    }
  },

  deleteButton: {
    color: 'white',
    backgroundColor: '#dc3545',
    '&:hover': {
      backgroundColor: '#c82333'
    }
  },

  pagination: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    marginTop: 24,
    padding: '16px 0'
  },

  pageButton: {
    width: 36,
    height: 36,
    borderRadius: 8,
    border: '1px solid #e0e0e0',
    backgroundColor: 'white',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    '&:hover:not(:disabled)': {
      backgroundColor: '#f8f9fa',
      borderColor: '#195cd7'
    },
    '&:disabled': {
      opacity: 0.5,
      cursor: 'not-allowed'
    }
  },

  pageInfo: {
    fontSize: 14,
    color: '#55565d',
    fontWeight: 500
  },

  actionButtons: {
    display: 'flex',
    gap: 8
  },

  responsiveButton: {
    '@media (max-width:768px)': {
      fontSize: '12px !important',
      padding: '6px 12px !important'
    }
  },

  // Responsive adjustments
  '@media (max-width:768px)': {
    hideOnMobile: {
      display: 'none'
    }
  }
});
