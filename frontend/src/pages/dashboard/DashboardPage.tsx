import { DashboardPageStyles } from "./DashboardPage.styles";

export const DashboardPage = () => {
  const classes = DashboardPageStyles();

  return (
    <div className={classes.container}>
      <div className={classes.firstSection}>
        <img
          src="background-logo.png"
          alt="Background Logo"
          className={classes.backgroundLogo}
        />
        <p className={classes.title}>
          Yapay Zeka ile Teklif Parametrelerinin PDF ve STEP Dosyalarından Analizi
        </p>
        <p className={classes.exp}>
          İşlem sonucunda teklif verilecek ürüne ait tüm analizler tamamlanacak,
          değerler hesaplanacak, 3D modeli görüntülenebilir duruma gelecek ve
          sonuçlar excel olarak indirilebilecektir. <br />
          <span>
            Step dosyasını ayrıca yüklemenize gerek yok. Sistem PDF'in içinden
            dosyayı otomatik bulup işlem yapar.
          </span>
        </p>
        <div className={classes.uploadSection}>
          <div className={classes.fileSelection}>
            <button className={classes.fileSelectionButton}>Choose Files</button>
            <p className={classes.fileSelectionText}>No files selected</p>
          </div>
          <button className={classes.uploadButton}>Yükle ve Tara</button>
        </div>
      </div>
    </div>
  );
};
