import { createUseStyles } from "react-jss";

export const DashboardPageStyles = createUseStyles({
  container: {
    display: 'flex',
    flexDirection: 'column',
    rowGap: 0,
    width: '100%',
    height: 'auto',
    marginTop: 80,
    padding: '0px 100px',
    boxSizing: 'border-box',
    '@media (max-width:1000px)': {
      padding: '0px 12px',
    },
  },
  navbar: {
    display: 'flex',
    width: '100%',
    height: 80,
    position: 'fixed',
    top: 0,
    left: 0,
    backgroundColor: '#e6e8ec',
    paddingLeft: 100,
    paddingRight: 100,
    alignItems: 'center',
    justifyContent: 'space-between',
    boxSizing: 'border-box',
    overflow: 'hidden',
    '@media (max-width:1000px)': {
      paddingLeft: 24,
      paddingRight: 24,
    },
  },
  logo: {
    height: 32,
    width: 'auto',
    objectFit: 'contain',
    '@media (max-width:1000px)': {
      height: 24,
    },
  },
  profileSection: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 8,
    cursor: 'pointer',
    '@media (max-width:1000px)': {
      columnGap: 4,
    },
  },
  profileIcon: {
    width: 32,
    height: 32,
    '@media (max-width:1000px)': {
      width: 24,
      height: 24,
    },
  },
  profileName: {
    fontSize: 16,
    fontWeight: 400,
    color: '#181a25',
    '@media (max-width:1000px)': {
      fontSize: 14,
    },
  },
  icon: {
    height: 24,
    width: 24,
  },
  firstSection: {
    display: 'flex',
    flexDirection: 'column',
    width: '100%',
    minHeight: 'calc(100vh - 80px)',
    boxSizing: 'border-box',
    rowGap: 32,
    alignItems: 'center',
    justifyContent: 'start',
    paddingTop: 32,
    '@media (max-width:1000px)': {
      rowGap: 24,
      paddingTop: 24,
    },
  },
  backgroundLogo: {
    height: 100,
    width: 'auto',
    '@media (max-width:1000px)': {
      width: 250,
      height: 'auto',
    },
  },
  title: {
    fontSize: 24,
    fontWeight: 600,
    color: '#181a25',
    textAlign: 'center',
    '@media (max-width:1000px)': {
      fontSize: 18,
    },
  },
  exp: {
    fontSize: 14,
    fontWeight: 400,
    color: '#55565d',
    textAlign: 'center',
    width: '80%',
    '@media (max-width:1000px)': {
      fontSize: 12,
      width: '100%',
    },
    '& span': {
      fontStyle: 'italic',
    },
  },
  uploadSection: {
    width: '100%',
    height: 'auto',
    boxSizing: 'border-box',
    padding: 24,
    backgroundColor: 'white',
    borderRadius: 16,
    display: 'flex',
    flexDirection: 'column',
    rowGap: 16,
    '@media (max-width:1000px)': {
      padding: 16,
      borderRadius: 12,
      rowGap: 12,
    },
  },
  fileSelection: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
    columnGap: 8,
    boxSizing: 'border-box',
    padding: 8,
    width: '100%',
    border: '1px solid #181a2520',
    borderRadius: 4,
    backgroundColor: '#181a2505',
  },
  fileSelectionButton: {
    border: 'none',
    backgroundColor: '#181a2520',
    color: '#181a25',
    padding: '4px 8px',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 14,
    transition: 'background 0.2s',
    '&:hover': {
      backgroundColor: '#181a2530',
    },
    '&:active': {
      backgroundColor: '#181a2540',
    },
    '@media (max-width:1000px)': {
      fontSize: 12,
    },
  },
  fileSelectionText: {
    fontSize: 14,
    fontWeight: 400,
    color: '#55565d',
    '@media (max-width:1000px)': {
      fontSize: 12,
    },
  },
  uploadButton: {
    border: 'none',
    backgroundColor: '#1f6eff',
    color: 'white',
    width: '100%',
    boxSizing: 'border-box',
    padding: 12,
    borderRadius: 4,
    cursor: 'pointer',
    transition: 'background 0.2s',
    fontSize: 16,
    fontWeight: 500,
    '&:hover': {
      backgroundColor: '#1c67f0',
    },
    '&:active': {
      backgroundColor: '#195cd7',
    },
    '@media (max-width:1000px)': {
      fontSize: 14,
    },
  },
})