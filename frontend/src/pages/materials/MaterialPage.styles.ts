import { createUseStyles } from "react-jss";
import { px2rem } from "../../utils/px2rem";

export const MaterialPageStyles = createUseStyles({
  // Ana container
  container: {
    padding: px2rem(32),
    maxWidth: '1200px',
    margin: '0 auto',
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      padding: px2rem(24),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      padding: px2rem(16),
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      padding: px2rem(12),
    },
  },

  // Sayfa başlığı
  pageTitle: {
    marginBottom: px2rem(32),
    textAlign: 'center',
    fontSize: px2rem(32),
    fontWeight: '600',
    color: '#181a25',
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      fontSize: px2rem(28),
      marginBottom: px2rem(24),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      fontSize: px2rem(24),
      marginBottom: px2rem(20),
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      fontSize: px2rem(20),
      marginBottom: px2rem(16),
    },
  },

  // Card container
  cardContainer: {
    marginBottom: px2rem(32),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      marginBottom: px2rem(20),
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      marginBottom: px2rem(16),
    },
    
    // Card içeriği
    '& .p-card': {
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      borderRadius: px2rem(12),
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        borderRadius: px2rem(8),
      },
    },
    
    '& .p-card-title': {
      fontSize: px2rem(18),
      fontWeight: '600',
      marginBottom: px2rem(16),
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        fontSize: px2rem(16),
        marginBottom: px2rem(12),
      },
    },
    
    '& .p-card-content': {
      padding: px2rem(24),
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        padding: px2rem(16),
      },
      
      // Küçük mobil cihazlar
      "@media (max-width: 480px)": {
        padding: px2rem(12),
      },
    },
  },

  // Form grid (responsive)
  formGrid: {
    display: 'grid',
    gap: px2rem(16),
    alignItems: 'end',
    
    // Desktop: 4 columns
    "&.grid-4": {
      gridTemplateColumns: '2fr 2fr 1fr auto',
      
      // Tablet: 2x2 grid
      "@media (max-width: 1024px)": {
        gridTemplateColumns: '1fr 1fr',
        gridTemplateRows: 'auto auto',
        
        '& > :nth-child(3)': {
          gridColumn: '1',
        },
        '& > :nth-child(4)': {
          gridColumn: '2',
        },
      },
      
      // Mobil: stacked
      "@media (max-width: 768px)": {
        gridTemplateColumns: '1fr',
        gridTemplateRows: 'auto auto auto auto',
        
        '& > *': {
          gridColumn: '1 !important',
        },
      },
    },
    
    // Desktop: 3 columns
    "&.grid-3": {
      gridTemplateColumns: '1fr 1fr auto',
      
      // Tablet: 2+1 layout
      "@media (max-width: 1024px)": {
        gridTemplateColumns: '1fr 1fr',
        gridTemplateRows: 'auto auto',
        
        '& > :nth-child(3)': {
          gridColumn: '1 / -1',
          justifySelf: 'center',
        },
      },
      
      // Mobil: stacked
      "@media (max-width: 768px)": {
        gridTemplateColumns: '1fr',
        
        '& > *': {
          gridColumn: '1 !important',
        },
      },
    },
  },

  // Form field wrapper
  fieldWrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: px2rem(8),
    
    // Label stilleri
    '& label': {
      fontSize: px2rem(14),
      fontWeight: '500',
      color: '#333',
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        fontSize: px2rem(13),
      },
    },
    
    // Required indicator
    '& .required': {
      color: '#dc3545',
    },
  },

  // Button responsive styles
  responsiveButton: {
    minHeight: px2rem(40),
    padding: `${px2rem(10)} ${px2rem(16)}`,
    fontSize: px2rem(14),
    fontWeight: '500',
    borderRadius: px2rem(6),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      width: '100%',
      minHeight: px2rem(44), // Daha kolay dokunma
      fontSize: px2rem(15),
      padding: `${px2rem(12)} ${px2rem(16)}`,
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      fontSize: px2rem(14),
      padding: `${px2rem(10)} ${px2rem(14)}`,
    },
  },

  // DataTable responsive wrapper
  tableWrapper: {
    overflowX: 'auto',
    marginTop: px2rem(16),
    borderRadius: px2rem(8),
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      marginTop: px2rem(12),
      borderRadius: px2rem(6),
      
      // Table responsive styles
      '& .p-datatable': {
        minWidth: '600px', // Minimum width to prevent crushing
      },
      
      '& .p-datatable-thead th': {
        fontSize: px2rem(12),
        padding: `${px2rem(8)} ${px2rem(6)}`,
        whiteSpace: 'nowrap',
      },
      
      '& .p-datatable-tbody td': {
        fontSize: px2rem(12),
        padding: `${px2rem(8)} ${px2rem(6)}`,
      },
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      '& .p-datatable': {
        minWidth: '500px',
      },
      
      '& .p-datatable-thead th': {
        fontSize: px2rem(11),
        padding: `${px2rem(6)} ${px2rem(4)}`,
      },
      
      '& .p-datatable-tbody td': {
        fontSize: px2rem(11),
        padding: `${px2rem(6)} ${px2rem(4)}`,
      },
    },
  },

  // Badge container (alias'lar için)
  badgeContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: px2rem(4),
    maxWidth: '300px',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      maxWidth: '200px',
    },
    
    '& .p-badge': {
      fontSize: px2rem(11),
      padding: `${px2rem(2)} ${px2rem(6)}`,
      cursor: 'pointer',
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        fontSize: px2rem(10),
        padding: `${px2rem(1)} ${px2rem(4)}`,
      },
      
      '&:hover': {
        backgroundColor: '#dc3545 !important',
        borderColor: '#dc3545 !important',
      },
    },
  },

  // Action buttons container
  actionButtons: {
    display: 'flex',
    gap: px2rem(8),
    justifyContent: 'center',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      flexDirection: 'column',
      gap: px2rem(4),
    },
    
    '& .p-button': {
      minWidth: px2rem(32),
      minHeight: px2rem(32),
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        width: '100%',
        minHeight: px2rem(36),
        justifyContent: 'center',
      },
    },
  },

  // Dialog responsive
  responsiveDialog: {
    // Dialog özel stilleri
    '& .p-dialog': {
      width: '90vw',
      maxWidth: '500px',
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        width: '95vw',
        maxWidth: 'none',
        margin: px2rem(10),
      },
    },
    
    '& .p-dialog-content': {
      padding: px2rem(20),
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        padding: px2rem(16),
      },
    },
  },

  // Form dialog content
  dialogForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: px2rem(16),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      gap: px2rem(12),
    },
  },

  // Dialog buttons
  dialogButtons: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: px2rem(8),
    marginTop: px2rem(16),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      flexDirection: 'column-reverse',
      gap: px2rem(8),
      marginTop: px2rem(12),
      
      '& .p-button': {
        width: '100%',
        justifyContent: 'center',
      },
    },
  },

  // Empty state
  emptyState: {
    textAlign: 'center',
    padding: px2rem(40),
    color: '#666',
    fontSize: px2rem(14),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      padding: px2rem(24),
      fontSize: px2rem(13),
    },
  },

  // Loading state
  loadingState: {
    textAlign: 'center',
    padding: px2rem(20),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      padding: px2rem(16),
    },
  },

  // Scroll hint for tables
  scrollHint: {
    display: 'none',
    fontSize: px2rem(12),
    color: '#666',
    textAlign: 'center',
    marginTop: px2rem(8),
    fontStyle: 'italic',
    
    // Mobilde göster
    "@media (max-width: 768px)": {
      display: 'block',
    },
  },

  // Utility classes
  hideOnMobile: {
    "@media (max-width: 768px)": {
      display: 'none !important',
    },
  },

  showOnMobile: {
    display: 'none',
    
    "@media (max-width: 768px)": {
      display: 'block !important',
    },
  },

  // Spacing utilities
  spacingLarge: {
    marginBottom: px2rem(32),
    
    "@media (max-width: 768px)": {
      marginBottom: px2rem(20),
    },
  },

  spacingMedium: {
    marginBottom: px2rem(20),
    
    "@media (max-width: 768px)": {
      marginBottom: px2rem(16),
    },
  },

  spacingSmall: {
    marginBottom: px2rem(12),
    
    "@media (max-width: 768px)": {
      marginBottom: px2rem(8),
    },
  },
});