// src/pages/auth/AuthPage.tsx
import React, { useState } from 'react';
import { Form, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { AuthPageStyle } from './AuthPage.style';
import { AuthPageLoginTypes } from './AuthPage.types';
import { TextField } from '../../components/TextField/TextField';
import { Button } from 'primereact/button';
import { authService } from '../../services/authService';

export const AuthPage = () => {
  const classes = AuthPageStyle();
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [loginError, setLoginError] = useState<string>('');

  const loginHandler = async (formData: AuthPageLoginTypes) => {
    setIsLoading(true);
    setLoginError('');

    try {
      const response = await authService.login({
        username: formData.username,
        password: formData.password
      });

      if (response.success) {
        message.success('Giriş başarılı! Yönlendiriliyorsunuz...');

        // Kısa bir gecikme ile kullanıcı deneyimini iyileştir
        setTimeout(() => {
          navigate('/');
        }, 1000);
      } else {
        setLoginError(response.message || 'Giriş başarısız');
        message.error(response.message || 'Kullanıcı adı veya şifre hatalı');
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Bağlantı hatası';
      setLoginError(errorMessage);
      message.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = () => {
    message.info('Şifre sıfırlama özelliği yakında eklenecek');
  };

  // Zaten giriş yapmışsa ana sayfaya yönlendir
  React.useEffect(() => {
    if (authService.isAuthenticated()) {
      navigate('/');
    }
  }, [navigate]);

  return (
    <div className={classes.authContainer}>
      <img
        src='/login.png'
        className={classes.authImage}
        alt='Login'
      />
      <div className={classes.authDiv}>
        <img
          src='/logo.svg'
          className={classes.authLogo}
          alt='Logo'
        />
        <p className={classes.authTitle}>Panel Giriş Yap</p>

        {loginError && (
          <div
            style={{
              color: '#dc3545',
              backgroundColor: '#f8d7da',
              border: '1px solid #f5c6cb',
              borderRadius: '4px',
              padding: '12px',
              marginBottom: '16px',
              fontSize: '14px'
            }}>
            ⚠️ {loginError}
          </div>
        )}

        <div className={classes.inputContainer}>
          <Form
            name='login'
            initialValues={{
              username: '',
              password: ''
            }}
            form={form}
            onFinish={loginHandler}
            autoComplete='off'>
            <Form.Item
              name='username'
              rules={[
                {
                  required: true,
                  message: 'Lütfen kullanıcı adını giriniz.'
                },
                {
                  min: 3,
                  message: 'Kullanıcı adı en az 3 karakter olmalı.'
                }
              ]}>
              <TextField
                id='username'
                label='Kullanıcı Adı'
                placeholder='Kullanıcı adınızı giriniz'
                fullWidth
                required
                disabled={isLoading}
              />
            </Form.Item>

            <Form.Item
              name='password'
              rules={[
                {
                  required: true,
                  message: 'Lütfen şifrenizi giriniz.'
                },
                {
                  min: 6,
                  message: 'Şifre en az 6 karakter olmalı.'
                }
              ]}>
              <TextField
                id='password'
                type='password'
                label='Şifre'
                placeholder='Şifrenizi giriniz'
                fullWidth
                required
                disabled={isLoading}
              />
            </Form.Item>

            <div className={classes.formFooter}>
              <a
                href='#'
                onClick={(e) => {
                  e.preventDefault();
                  handleForgotPassword();
                }}
                style={{
                  color: '#195cd7',
                  textDecoration: 'none',
                  fontSize: '14px'
                }}>
                Şifremi Unuttum
              </a>

              <Form.Item style={{ margin: 0 }}>
                <Button
                  type='submit'
                  label={isLoading ? 'Giriş Yapılıyor...' : 'Giriş Yap'}
                  className='full-width'
                  disabled={isLoading}
                  loading={isLoading}
                  style={{
                    backgroundColor: isLoading ? '#cccccc' : '#195cd7',
                    borderColor: isLoading ? '#cccccc' : '#195cd7',
                    color: 'white',
                    padding: '12px 24px',
                    fontSize: '16px',
                    fontWeight: '500',
                    borderRadius: '4px',
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    transition: 'all 0.3s ease'
                  }}
                />
              </Form.Item>
            </div>
          </Form>

          {/* Test Kullanıcı Bilgileri (Development için) */}
          {process.env.NODE_ENV === 'development' && (
            <div
              style={{
                marginTop: '24px',
                padding: '16px',
                backgroundColor: '#f8f9fa',
                borderRadius: '8px',
                border: '1px solid #dee2e6'
              }}>
              <h4
                style={{
                  margin: '0 0 12px 0',
                  fontSize: '14px',
                  color: '#495057'
                }}>
                Test Hesapları:
              </h4>
              <div style={{ fontSize: '12px', color: '#6c757d' }}>
                <p style={{ margin: '4px 0' }}>
                  <strong>Admin:</strong> admin / engteklif
                </p>
                <p style={{ margin: '4px 0' }}>
                  <strong>User:</strong> user / engteklif
                </p>
              </div>
              <div style={{ marginTop: '12px' }}>
                <Button
                  type='button'
                  label='Admin ile Giriş'
                  size='small'
                  outlined
                  onClick={() => {
                    form.setFieldsValue({
                      username: 'admin',
                      password: 'engteklif'
                    });
                  }}
                  style={{ marginRight: '8px', fontSize: '12px' }}
                />
                <Button
                  type='button'
                  label='Test User ile Giriş'
                  size='small'
                  outlined
                  onClick={() => {
                    form.setFieldsValue({
                      username: 'user',
                      password: 'engteklif'
                    });
                  }}
                  style={{ fontSize: '12px' }}
                />
              </div>
            </div>
          )}

          {/* API Bağlantı Durumu */}
          <div
            style={{
              marginTop: '16px',
              fontSize: '12px',
              color: '#6c757d',
              textAlign: 'center'
            }}>
            API Endpoint:{' '}
            {process.env.REACT_APP_API_URL || 'http://localhost:5050'}
          </div>
        </div>
      </div>
    </div>
  );
};
