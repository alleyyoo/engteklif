import { createUseStyles } from "react-jss";
import { px2rem } from "../../utils/px2rem";

export const AuthPageStyle = createUseStyles({
  authContainer: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    columnGap: px2rem(48),
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
    height: "100vh",
    boxSizing: "border-box",
    padding: `0 ${px2rem(100)}`,
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      padding: `0 ${px2rem(60)}`,
      columnGap: px2rem(32),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      gridTemplateColumns: "1fr",
      gridTemplateRows: "auto 1fr",
      rowGap: px2rem(24),
      padding: `${px2rem(20)} ${px2rem(20)}`,
      height: "100vh",
      overflowY: "auto",
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      padding: `${px2rem(16)} ${px2rem(16)}`,
      rowGap: px2rem(16),
    },
  },
  
  authImage: {
    width: "100%",
    height: "80vh",
    objectFit: "cover",
    borderRadius: px2rem(40),
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      height: "70vh",
      borderRadius: px2rem(32),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      height: px2rem(200),
      borderRadius: px2rem(24),
      order: 1,
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      height: px2rem(150),
      borderRadius: px2rem(16),
      display: "none", // Mobilde resim gizlensin
    },
  },
  
  authDiv: {
    display: "flex",
    flexDirection: "column",
    rowGap: px2rem(24),
    width: "100%",
    padding: px2rem(32),
    boxSizing: "border-box",
    borderRadius: px2rem(16),
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      padding: px2rem(24),
      rowGap: px2rem(20),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      padding: px2rem(20),
      rowGap: px2rem(16),
      order: 2,
      borderRadius: px2rem(12),
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      padding: px2rem(16),
      rowGap: px2rem(12),
    },
  },
  
  authLogo: {
    height: px2rem(48),
    width: "auto",
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      height: px2rem(40),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      height: px2rem(36),
      alignSelf: "center",
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      height: px2rem(32),
    },
  },
  
  authTitle: {
    fontSize: px2rem(48),
    fontWeight: 400,
    textAlign: "center",
    margin: 0,
    
    // Tablet responsive
    "@media (max-width: 1024px)": {
      fontSize: px2rem(40),
    },
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      fontSize: px2rem(32),
      lineHeight: 1.2,
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      fontSize: px2rem(24),
      lineHeight: 1.3,
    },
  },
  
  inputContainer: {
    width: "100%",
    
    // Mobil için ek stillendirme gerekirse
    "@media (max-width: 768px)": {
      // Input alanları için mobil optimizasyonu
    },
  },
  
  formFooter: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    
    // Mobil responsive
    "@media (max-width: 768px)": {
      flexDirection: "column",
      alignItems: "center",
      rowGap: px2rem(12),
      textAlign: "center",
    },
    
    // Küçük mobil cihazlar
    "@media (max-width: 480px)": {
      rowGap: px2rem(8),
    },
  },
});