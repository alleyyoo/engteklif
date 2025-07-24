// MaterialPage.styles.ts
import { createUseStyles } from 'react-jss';

export const MaterialPageStyles = createUseStyles({
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

  cacheManagement: {
    display: 'flex',
    alignItems: 'center',
    gap: 16
  },

  cacheButton: {
    padding: '10px 20px',
    fontSize: 14,
    fontWeight: 500,
    color: 'white',
    backgroundColor: '#17a2b8',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 0.3s',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    '&:hover': {
      backgroundColor: '#138496',
      transform: 'translateY(-1px)',
      boxShadow: '0 4px 12px rgba(23, 162, 184, 0.3)'
    },
    '&:disabled': {
      opacity: 0.7,
      cursor: 'not-allowed',
      transform: 'none'
    }
  },

  cacheButtonLoading: {
    backgroundColor: '#6c757d'
  },

  cacheInfo: {
    fontSize: 12,
    color: '#6c757d'
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
    width: '35%',
    minWidth: 350,
    maxWidth: 450,
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
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    '@media (max-width:1000px)': {
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

  formCard: {
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    border: '1px solid #e0e0e0',
    '& h4': {
      fontSize: 16,
      fontWeight: 600,
      color: '#181a25',
      margin: '0 0 16px 0'
    }
  },

  formFields: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16
  },

  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    '& label': {
      fontSize: 13,
      fontWeight: 500,
      color: '#55565d'
    }
  },

  required: {
    color: '#dc3545'
  },

  inputField: {
    padding: '10px 12px',
    fontSize: 14,
    borderRadius: 6,
    border: '1px solid #d0d0d0',
    transition: 'all 0.2s',
    outline: 'none',
    '&:focus': {
      borderColor: '#195cd7',
      boxShadow: '0 0 0 2px rgba(25, 92, 215, 0.1)'
    }
  },

  dropdownField: {
    width: '100%',
    '& .p-dropdown': {
      width: '100%',
      borderRadius: 6,
      border: '1px solid #d0d0d0',
      backgroundColor: 'white',
      transition: 'all 0.2s',
      height: '42px', // inputField ile aynı yükseklik
      '&:not(.p-disabled):hover': {
        borderColor: '#195cd7'
      },
      '&.p-focus': {
        borderColor: '#195cd7',
        boxShadow: '0 0 0 2px rgba(25, 92, 215, 0.1)'
      }
    },
    '& .p-dropdown-label': {
      padding: '10px 12px',
      fontSize: 14,
      color: '#181a25',
      '&.p-placeholder': {
        color: '#999'
      }
    },
    '& .p-dropdown-trigger': {
      width: '2.5rem',
      color: '#6c757d'
    }
  },

  submitButton: {
    padding: '12px 20px',
    fontSize: 14,
    fontWeight: 500,
    color: 'white',
    backgroundColor: '#10b86b',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 0.3s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    '&:hover': {
      backgroundColor: '#0ea760',
      transform: 'translateY(-1px)',
      boxShadow: '0 4px 12px rgba(16, 184, 107, 0.3)'
    }
  },

  submitButtonDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
    '&:hover': {
      backgroundColor: '#10b86b',
      transform: 'none',
      boxShadow: 'none'
    }
  },

  infoPanel: {
    backgroundColor: '#fff3cd',
    borderLeft: '4px solid #ffc107',
    borderRadius: 6,
    padding: 16,
    display: 'flex',
    gap: 12,
    alignItems: 'flex-start',
    '& i': {
      color: '#856404',
      fontSize: 16,
      marginTop: 2
    },
    '& p': {
      margin: 0,
      fontSize: 13,
      color: '#856404',
      lineHeight: 1.5
    }
  },

  tabNavigation: {
    gap: 8,
    paddingBottom: 0,
    '@media (max-width:1000px)': {
      padding: 16,
      paddingBottom: 0
    }
  },

  tabButton: {
    padding: '12px 24px',
    fontSize: 14,
    fontWeight: 500,
    color: '#6c757d',
    backgroundColor: 'transparent',
    border: 'none',
    borderBottom: '3px solid transparent',
    cursor: 'pointer',
    transition: 'all 0.2s',
    '&:hover': {
      color: '#495057',
      backgroundColor: '#f0f0f0'
    }
  },

  tabButtonActive: {
    color: '#195cd7',
    borderBottomColor: '#195cd7',
    backgroundColor: 'white'
  },

  contentArea: {
    flex: 1,
    padding: 24,
    overflow: 'auto',
    backgroundColor: '#f8f9fa',
    '@media (max-width:1000px)': {
      padding: 16
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
    minHeight: 300,
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

  cardGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
    '@media (max-width:768px)': {
      gridTemplateColumns: '1fr'
    }
  },

  materialCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    border: '1px solid #e0e0e0',
    padding: 20,
    transition: 'all 0.3s',
    '&:hover': {
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      transform: 'translateY(-2px)'
    }
  },

  materialHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16
  },

  materialName: {
    fontSize: 18,
    fontWeight: 600,
    color: '#181a25',
    margin: 0
  },

  materialActions: {
    display: 'flex',
    gap: 8
  },

  iconButton: {
    width: 32,
    height: 32,
    borderRadius: 6,
    border: '1px solid #d0d0d0',
    backgroundColor: 'white',
    color: '#6c757d',
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    '&:hover': {
      backgroundColor: '#f8f9fa',
      borderColor: '#195cd7',
      color: '#195cd7'
    }
  },

  deleteButton: {
    '&:hover': {
      borderColor: '#dc3545',
      color: '#dc3545',
      backgroundColor: '#fff5f5'
    }
  },

  materialInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    marginBottom: 16
  },

  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },

  infoLabel: {
    fontSize: 13,
    color: '#6c757d'
  },

  infoValue: {
    fontSize: 14,
    fontWeight: 500,
    color: '#181a25'
  },

  materialAliases: {
    borderTop: '1px solid #f0f0f0',
    paddingTop: 12,
    '& .aliasLabel': {
      fontSize: 12,
      color: '#6c757d',
      marginBottom: 8,
      display: 'block'
    }
  },

  aliasContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6
  },

  aliasChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    padding: '4px 10px',
    fontSize: 12,
    backgroundColor: '#e9ecef',
    borderRadius: 16,
    cursor: 'pointer',
    transition: 'all 0.2s',
    '&:hover': {
      backgroundColor: '#dc3545',
      color: 'white'
    }
  },

  aliasDelete: {
    fontSize: 16,
    fontWeight: 'bold',
    opacity: 0.7
  },

  priceGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
    '@media (max-width:768px)': {
      gridTemplateColumns: '1fr'
    }
  },

  priceCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    border: '1px solid #e0e0e0',
    padding: 20,
    transition: 'all 0.3s',
    '&:hover': {
      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      transform: 'translateY(-2px)'
    }
  },

  priceHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12
  },

  priceHeaderRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 12
  },

  priceCardActions: {
    display: 'flex',
    gap: 8
  },

  priceMaterialName: {
    fontSize: 16,
    fontWeight: 600,
    color: '#181a25',
    margin: 0,
    flex: 1
  },

  priceValue: {
    fontSize: 24,
    fontWeight: 700
  },

  priceUnit: {
    fontSize: 14,
    fontWeight: 400,
    color: '#6c757d'
  },

  priceInfo: {
    paddingTop: 8,
    borderTop: '1px solid #f0f0f0'
  },

  densityInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 13,
    color: '#6c757d',
    '& i': {
      fontSize: 12
    }
  },

  priceActions: {
    display: 'none' // Bu satırı kaldırıyoruz çünkü artık üstte icon olarak gösteriyoruz
  },

  actionButton: {
    flex: 1,
    padding: '8px 16px',
    fontSize: 13,
    fontWeight: 500,
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
    transition: 'all 0.2s',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6
  },

  editButton: {
    color: '#195cd7',
    backgroundColor: '#e6f2ff',
    '&:hover': {
      backgroundColor: '#195cd7',
      color: 'white'
    }
  },

  deleteActionButton: {
    color: '#dc3545',
    backgroundColor: '#fff5f5',
    '&:hover': {
      backgroundColor: '#dc3545',
      color: 'white'
    }
  },

  dialog: {
    '& .p-dialog': {
      borderRadius: 12,
      boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
      maxWidth: 400,
      width: '90%'
    },
    '& .p-dialog-header': {
      borderRadius: '12px 12px 0 0',
      borderBottom: '1px solid #e0e0e0'
    }
  },

  dialogContent: {
    padding: 20
  },

  dialogField: {
    marginBottom: 20,
    '& label': {
      display: 'block',
      fontSize: 14,
      fontWeight: 500,
      color: '#55565d',
      marginBottom: 8
    }
  },

  dialogInput: {
    width: '100%',
    padding: '10px 12px',
    fontSize: 14,
    borderRadius: 6,
    border: '1px solid #d0d0d0',
    transition: 'all 0.2s',
    outline: 'none',
    '&:focus': {
      borderColor: '#195cd7',
      boxShadow: '0 0 0 2px rgba(25, 92, 215, 0.1)'
    }
  },

  dialogActions: {
    display: 'flex',
    gap: 12,
    marginTop: 24,
    paddingTop: 20,
    borderTop: '1px solid #f0f0f0'
  },

  cancelButton: {
    flex: 1,
    padding: '10px 20px',
    fontSize: 14,
    fontWeight: 500,
    color: '#6c757d',
    backgroundColor: 'white',
    border: '1px solid #6c757d',
    borderRadius: 6,
    cursor: 'pointer',
    transition: 'all 0.2s',
    '&:hover': {
      backgroundColor: '#6c757d',
      color: 'white'
    }
  },

  saveButton: {
    '&:hover': {
      backgroundColor: '#10b86b',
      color: 'white'
    }
  },

  cancelButton: {
    '&:hover': {
      backgroundColor: '#6c757d',
      color: 'white'
    }
  },

  saveActionButton: {
    color: 'white',
    backgroundColor: '#10b86b',
    '&:hover': {
      backgroundColor: '#0ea760'
    }
  },

  cancelActionButton: {
    color: '#6c757d',
    backgroundColor: '#f8f9fa',
    border: '1px solid #6c757d',
    '&:hover': {
      backgroundColor: '#6c757d',
      color: 'white'
    }
  },

  inlineEditInput: {
    padding: '6px 10px',
    fontSize: 18,
    fontWeight: 600,
    borderRadius: 6,
    border: '2px solid #195cd7',
    outline: 'none',
    width: '100%',
    maxWidth: 200,
    backgroundColor: 'white',
    color: '#181a25',
    transition: 'all 0.2s',
    '&:focus': {
      boxShadow: '0 0 0 3px rgba(25, 92, 215, 0.1)'
    }
  },

  inlineEditInputSmall: {
    padding: '4px 8px',
    fontSize: 14,
    fontWeight: 500,
    borderRadius: 4,
    border: '1px solid #195cd7',
    outline: 'none',
    width: 100,
    textAlign: 'right',
    backgroundColor: 'white',
    color: '#181a25',
    transition: 'all 0.2s',
    '&:focus': {
      boxShadow: '0 0 0 2px rgba(25, 92, 215, 0.1)'
    }
  },

  priceEditContainer: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 4
  },

  dollarSign: {
    fontSize: 20,
    fontWeight: 700
  },

  priceEditInput: {
    padding: '4px 8px',
    fontSize: 20,
    fontWeight: 700,
    borderRadius: 6,
    outline: 'none',
    width: 80,
    textAlign: 'center',
    backgroundColor: 'white',
    transition: 'all 0.2s',
    '&:focus': {
      boxShadow: '0 0 0 3px rgba(16, 184, 107, 0.1)'
    },
    // Remove spinner arrows
    '&::-webkit-inner-spin-button, &::-webkit-outer-spin-button': {
      '-webkit-appearance': 'none',
      margin: 0
    },
    '-moz-appearance': 'textfield'
  },

  dropdownPanel: {
    '& .p-dropdown-panel': {
      borderRadius: 6,
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      border: '1px solid #e0e0e0'
    },
    '& .p-dropdown-items': {
      padding: '4px'
    },
    '& .p-dropdown-item': {
      borderRadius: 4,
      fontSize: 14,
      padding: '8px 12px',
      margin: '2px 0',
      transition: 'all 0.2s',
      '&:hover': {
        backgroundColor: '#f0f7ff'
      },
      '&.p-highlight': {
        backgroundColor: '#195cd7',
        color: 'white'
      }
    }
  },

  aliasLabel: {
    fontSize: 12,
    color: '#6c757d',
    marginBottom: 8,
    display: 'block'
  },

  // Legacy styles for compatibility
  responsiveButton: {
    '@media (max-width:768px)': {
      fontSize: '12px !important',
      padding: '6px 12px !important'
    }
  },

  hideOnMobile: {
    '@media (max-width:768px)': {
      display: 'none'
    }
  },

  badgeContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4
  },

  actionButtons: {
    display: 'flex',
    gap: 8
  }
});
