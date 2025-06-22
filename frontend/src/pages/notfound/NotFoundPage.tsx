// src/pages/NotFound/NotFoundPage.tsx
import React from 'react';
import { Button } from 'primereact/button';
import { useNavigate } from 'react-router-dom';

export const NotFoundPage = () => {
  const navigate = useNavigate();

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '2rem',
      textAlign: 'center',
      backgroundColor: '#f8f9fa'
    }}>
      <div style={{
        maxWidth: '500px',
        width: '100%'
      }}>
        <div style={{
          fontSize: '120px',
          fontWeight: 'bold',
          color: '#195cd7',
          marginBottom: '1rem',
          lineHeight: 1
        }}>
          404
        </div>
        
        <h1 style={{
          fontSize: '2rem',
          color: '#181a25',
          marginBottom: '1rem',
          fontWeight: '600'
        }}>
          Sayfa Bulunamadı
        </h1>
        
        <p style={{
          fontSize: '1.1rem',
          color: '#55565d',
          marginBottom: '2rem',
          lineHeight: 1.6
        }}>
          Aradığınız sayfa mevcut değil veya bu sayfaya erişim yetkiniz bulunmuyor.
        </p>
        
        <div style={{
          display: 'flex',
          gap: '1rem',
          justifyContent: 'center',
          flexWrap: 'wrap'
        }}>
          <Button
            label="Ana Sayfaya Dön"
            icon="pi pi-home"
            onClick={() => navigate('/')}
            style={{
              backgroundColor: '#195cd7',
              borderColor: '#195cd7',
              padding: '12px 24px',
              fontSize: '16px'
            }}
          />
          
          <Button
            label="Geri Git"
            icon="pi pi-arrow-left"
            outlined
            onClick={() => navigate(-1)}
            style={{
              padding: '12px 24px',
              fontSize: '16px'
            }}
          />
        </div>
        
        <div style={{
          marginTop: '3rem',
          padding: '1.5rem',
          backgroundColor: 'white',
          borderRadius: '8px',
          border: '1px solid #e0e0e0'
        }}>
          <h3 style={{
            fontSize: '1.2rem',
            color: '#181a25',
            marginBottom: '1rem'
          }}>
            Yardıma mı ihtiyacınız var?
          </h3>
          
          <p style={{
            fontSize: '14px',
            color: '#55565d',
            marginBottom: '1rem'
          }}>
            Eğer bu sayfaya erişmeniz gerektiğini düşünüyorsanız:
          </p>
          
          <ul style={{
            textAlign: 'left',
            fontSize: '14px',
            color: '#55565d',
            paddingLeft: '1.5rem'
          }}>
            <li>Doğru URL'yi girdiğinizden emin olun</li>
            <li>Yeterli yetkiye sahip olduğunuzu kontrol edin</li>
            <li>Sistem yöneticisi ile iletişime geçin</li>
          </ul>
        </div>
      </div>
    </div>
  );
};