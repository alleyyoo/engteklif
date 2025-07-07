// frontend/src/pages/cmm/CMMPage.styles.ts
import { createUseStyles } from "react-jss";
import { px2rem } from "../../utils/px2rem";

export const CMMPageStyles = createUseStyles({
  // Ana container
  container: {
    padding: px2rem(32),
    maxWidth: '1400px',
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

  // Stats container
  statsContainer: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: px2rem(16),
    marginBottom: px2rem(32),
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: px2rem(12),
      marginBottom: px2rem(24),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      gridTemplateColumns: '1fr',
      gap: px2rem(8),
      marginBottom: px2rem(20),
    },
  },

  // Stats card
  statsCard: {
    backgroundColor: '#f8f9fa',
    border: '1px solid #e9ecef',
    borderRadius: px2rem(12),
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    
    '& .p-card-content': {
      padding: px2rem(16),
      textAlign: 'center',
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        padding: px2rem(12),
      },
    },
  },

  // Stat item
  statItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: px2rem(8),
  },

  // Stat number
  statNumber: {
    fontSize: px2rem(24),
    fontWeight: 'bold',
    color: '#195cd7',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      fontSize: px2rem(20),
    },
  },

  // Stat label
  statLabel: {
    fontSize: px2rem(14),
    color: '#6c757d',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      fontSize: px2rem(12),
    },
  },

  // Card container
  cardContainer: {
    marginBottom: px2rem(32),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      marginBottom: px2rem(20),
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

  // Upload section
  uploadSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: px2rem(16),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      gap: px2rem(12),
    },
  },

  // File selection area
  fileSelection: {
    display: 'flex',
    alignItems: 'center',
    gap: px2rem(12),
    padding: px2rem(16),
    border: '2px dashed #dee2e6',
    borderRadius: px2rem(8),
    backgroundColor: '#f8f9fa',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      flexDirection: 'column',
      gap: px2rem(8),
      padding: px2rem(12),
      textAlign: 'center',
    },
  },

  // File count
  fileCount: {
    fontSize: px2rem(14),
    color: '#6c757d',
    fontWeight: '500',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      fontSize: px2rem(13),
    },
  },

  // File list
  fileList: {
    display: 'flex',
    flexDirection: 'column',
    gap: px2rem(8),
    maxHeight: px2rem(200),
    overflowY: 'auto',
    border: '1px solid #dee2e6',
    borderRadius: px2rem(6),
    padding: px2rem(12),
    backgroundColor: '#ffffff',
  },

  // File item
  fileItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: px2rem(8),
    backgroundColor: '#f8f9fa',
    borderRadius: px2rem(4),
    border: '1px solid #e9ecef',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      flexDirection: 'column',
      gap: px2rem(4),
      alignItems: 'flex-start',
      padding: px2rem(6),
    },
  },

  // File info
  fileInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: px2rem(2),
    flex: 1,
  },

  // File name
  fileName: {
    fontSize: px2rem(14),
    fontWeight: '500',
    color: '#181a25',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      fontSize: px2rem(13),
    },
  },

  // File size
  fileSize: {
    fontSize: px2rem(12),
    color: '#6c757d',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      fontSize: px2rem(11),
    },
  },

  // Processing info
  processingInfo: {
    marginTop: px2rem(16),
    
    '& .p-panel': {
      border: '1px solid #e9ecef',
      borderRadius: px2rem(6),
    },
    
    '& .p-panel-header': {
      backgroundColor: '#f8f9fa',
      borderBottom: '1px solid #e9ecef',
      padding: px2rem(12),
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        padding: px2rem(8),
      },
    },
    
    '& .p-panel-content': {
      padding: px2rem(16),
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        padding: px2rem(12),
      },
    },
  },

  // Feature list
  featureList: {
    margin: 0,
    paddingLeft: px2rem(20),
    
    '& li': {
      marginBottom: px2rem(8),
      fontSize: px2rem(14),
      color: '#495057',
      lineHeight: 1.5,
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        fontSize: px2rem(13),
        marginBottom: px2rem(6),
      },
    },
  },

  // Progress section
  progressSection: {
    padding: px2rem(16),
    backgroundColor: '#e8f5e8',
    borderRadius: px2rem(6),
    border: '1px solid #c3e6c3',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      padding: px2rem(12),
    },
  },

  // Progress text
  progressText: {
    marginTop: px2rem(8),
    fontSize: px2rem(14),
    color: '#28a745',
    textAlign: 'center',
    fontWeight: '500',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      fontSize: px2rem(13),
    },
  },

  // Upload button
  uploadButton: {
    alignSelf: 'center',
    minWidth: px2rem(200),
    minHeight: px2rem(50),
    fontSize: px2rem(16),
    fontWeight: '600',
    borderRadius: px2rem(8),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      width: '100%',
      minHeight: px2rem(48),
      fontSize: px2rem(15),
    },
  },

  // Responsive button
  responsiveButton: {
    minHeight: px2rem(40),
    padding: `${px2rem(10)} ${px2rem(16)}`,
    fontSize: px2rem(14),
    fontWeight: '500',
    borderRadius: px2rem(6),
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      width: '100%',
      minHeight: px2rem(44),
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
        minWidth: '700px', // Minimum width to prevent crushing
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
        minWidth: '600px',
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

  // Badge container
  badgeContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: px2rem(4),
    maxWidth: '200px',
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      maxWidth: '150px',
    },
    
    '& .p-badge': {
      fontSize: px2rem(11),
      padding: `${px2rem(2)} ${px2rem(6)}`,
      
      // Mobil responsive
      "@media (max-width: 768px)": {
        fontSize: px2rem(10),
        padding: `${px2rem(1)} ${px2rem(4)}`,
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

  // Empty state
  emptyState: {
    textAlign: 'center',
    padding: px2rem(40),
    color: '#6c757d',
    fontSize: px2rem(14),
    fontStyle: 'italic',
    backgroundColor: '#f8f9fa',
    borderRadius: px2rem(6),
    border: '1px solid #e9ecef',
    
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
    color: '#6c757d',
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