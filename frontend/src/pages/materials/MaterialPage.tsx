import React, { useState, useEffect } from 'react';
import { Button } from 'primereact/button';
import { InputText } from 'primereact/inputtext';
import { Dropdown } from 'primereact/dropdown';
import { DataTable } from 'primereact/datatable';
import { Column } from 'primereact/column';
import { Toast } from 'primereact/toast';
import { Dialog } from 'primereact/dialog';
import { Card } from 'primereact/card';
import { Badge } from 'primereact/badge';
import { ConfirmDialog, confirmDialog } from 'primereact/confirmdialog';
import { Toolbar } from 'primereact/toolbar';
import { MaterialPageStyles } from './MaterialPage.styles';

// Types
interface Material {
  id: string;
  name: string;
  aliases: string[];
  density?: number;
  price_per_kg?: number;
  category?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface MaterialPrice {
  id: string;
  material_name: string;
  price: number;
  density?: number;
  category?: string;
}

interface DropdownOption {
  label: string;
  value: string;
}

interface CacheRefreshResponse {
  success: boolean;
  message: string;
}

export const MaterialPage = () => {
  const classes = MaterialPageStyles();

  // State variables
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialPrices, setMaterialPrices] = useState<MaterialPrice[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'materials' | 'prices'>(
    'materials'
  );

  // Cache refresh state
  const [refreshingCache, setRefreshingCache] = useState(false);
  const [lastCacheRefresh, setLastCacheRefresh] = useState<Date | null>(null);

  // Form states
  const [selectedMaterial, setSelectedMaterial] = useState<string>('');
  const [newAliases, setNewAliases] = useState('');
  const [newMaterialName, setNewMaterialName] = useState('');
  const [newMaterialAliases, setNewMaterialAliases] = useState('');
  const [newMaterialDensity, setNewMaterialDensity] = useState('');
  const [selectedPriceMaterial, setSelectedPriceMaterial] =
    useState<string>('');
  const [materialPrice, setMaterialPrice] = useState('');

  // Edit states
  const [editingMaterialId, setEditingMaterialId] = useState<string | null>(
    null
  );
  const [editingPriceId, setEditingPriceId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<{ [key: string]: any }>({});

  const toast = React.useRef<Toast>(null);

  // API Helper function
  const apiRequest = async (endpoint: string, options: RequestInit = {}) => {
    const defaultOptions: RequestInit = {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
        'Content-Type': 'application/json'
      }
    };

    const response = await fetch(
      `${process.env.REACT_APP_API_URL || "http://localhost:5050"}${endpoint}`,
      {
        ...defaultOptions,
        ...options,
        headers: {
          ...defaultOptions.headers,
          ...options.headers,
        },
      }
    );

    const data = await response.json();
    return { response, data };
  };

  useEffect(() => {
    loadMaterials();
    loadMaterialPrices();
    loadLastCacheRefresh();
  }, []);

  // Load last cache refresh time from localStorage
  const loadLastCacheRefresh = () => {
    const lastRefresh = localStorage.getItem('lastMaterialCacheRefresh');
    if (lastRefresh) {
      setLastCacheRefresh(new Date(lastRefresh));
    }
  };

  // Cache refresh function
  const handleCacheRefresh = async () => {
    try {
      setRefreshingCache(true);

      console.log('🔄 Material cache refresh başlatılıyor...');

      const { data } = await apiRequest('/api/materials/refresh-cache', {
        method: 'POST'
      });

      if (data.success) {
        const now = new Date();
        setLastCacheRefresh(now);
        localStorage.setItem('lastMaterialCacheRefresh', now.toISOString());

        showSuccess(
          'Malzeme cache başarıyla yenilendi! Analiz sistemi güncel malzemelerle çalışacak.'
        );

        // Malzemeleri yeniden yükle
        await loadMaterials();
        await loadMaterialPrices();

        console.log('✅ Material cache refresh başarılı');
      } else {
        throw new Error(data.message || 'Cache yenileme başarısız');
      }
    } catch (error: any) {
      console.error('❌ Cache refresh hatası:', error);
      showError(`Cache yenileme hatası: ${error.message}`);
    } finally {
      setRefreshingCache(false);
    }
  };

  // Auto refresh cache after important operations
  const performOperationWithCacheRefresh = async (
    operation: () => Promise<void>,
    operationName: string
  ) => {
    try {
      await operation();
      console.log(`🔄 ${operationName} sonrası cache otomatik yenileniyor...`);
      await handleCacheRefresh();
    } catch (error) {
      console.error(`❌ ${operationName} ve cache refresh hatası:`, error);
      throw error;
    }
  };

  const loadMaterials = async () => {
    try {
      setLoading(true);
      const { data } = await apiRequest('/api/materials?limit=1000');

      if (data.success) {
        setMaterials(data.materials || []);
        console.log('Loaded materials:', data.materials?.length || 0);
      } else {
        showError(data.message || 'Malzemeler yüklenemedi');
      }
    } catch (error) {
      console.error('Materials loading error:', error);
      showError('Malzemeler yüklenirken hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  const loadMaterialPrices = async () => {
    try {
      const { data } = await apiRequest('/api/materials?limit=1000');

      if (data.success) {
        const pricesData =
          data.materials
            ?.filter((material: Material) => material.price_per_kg != null)
            ?.map((material: Material) => ({
              id: material.id,
              material_name: material.name,
              price: material.price_per_kg,
              density: material.density,
              category: material.category
            })) || [];

        setMaterialPrices(pricesData);
        console.log('Loaded material prices:', pricesData.length);
      }
    } catch (error) {
      console.log('Fiyat bilgileri yüklenemedi:', error);
    }
  };

  const showSuccess = (message: string) => {
    toast.current?.show({
      severity: 'success',
      summary: 'Başarılı',
      detail: message,
      life: 3000
    });
  };

  const showError = (message: string) => {
    toast.current?.show({
      severity: 'error',
      summary: 'Hata',
      detail: message,
      life: 3000
    });
  };

  // Add alias with cache refresh
  const handleAddAlias = async () => {
    if (!selectedMaterial || !newAliases.trim()) {
      showError('Malzeme seçin ve alias girin');
      return;
    }

    await performOperationWithCacheRefresh(async () => {
      const aliasArray = newAliases
        .split(',')
        .map((alias) => alias.trim())
        .filter((alias) => alias);

      const { data } = await apiRequest(
        `/api/materials/${selectedMaterial}/aliases`,
        {
          method: 'POST',
          body: JSON.stringify({ aliases: aliasArray })
        }
      );

      if (data.success) {
        showSuccess('Alias başarıyla eklendi');
        setSelectedMaterial('');
        setNewAliases('');
        await loadMaterials();
      } else {
        throw new Error(data.message || 'Alias eklenemedi');
      }
    }, 'Alias ekleme');
  };

  // Add new material with cache refresh
  const handleAddNewMaterial = async () => {
    if (!newMaterialName.trim()) {
      showError('Malzeme adı gerekli');
      return;
    }

    await performOperationWithCacheRefresh(async () => {
      const materialData = {
        name: newMaterialName.trim(),
        aliases: newMaterialAliases
          ? newMaterialAliases
              .split(',')
              .map((alias) => alias.trim())
              .filter((alias) => alias)
          : [],
        density: newMaterialDensity ? parseFloat(newMaterialDensity) : null
      };

      const { data } = await apiRequest('/api/materials', {
        method: 'POST',
        body: JSON.stringify(materialData)
      });

      if (data.success) {
        showSuccess('Malzeme başarıyla eklendi');
        setNewMaterialName('');
        setNewMaterialAliases('');
        setNewMaterialDensity('');
        await loadMaterials();
      } else {
        throw new Error(data.message || 'Malzeme eklenemedi');
      }
    }, 'Yeni malzeme ekleme');
  };

  // Add/update material price with cache refresh
  const handleAddMaterialPrice = async () => {
    if (!selectedPriceMaterial || !materialPrice) {
      showError('Malzeme seçin ve fiyat girin');
      return;
    }

    await performOperationWithCacheRefresh(async () => {
      const selectedMaterial = materials.find(
        (m) => m.name === selectedPriceMaterial
      );
      if (!selectedMaterial) {
        throw new Error('Seçilen malzeme bulunamadı');
      }

      const { data } = await apiRequest(
        `/api/materials/${selectedMaterial.id}`,
        {
          method: 'PUT',
          body: JSON.stringify({
            price_per_kg: parseFloat(materialPrice)
          })
        }
      );

      if (data.success) {
        showSuccess('Fiyat başarıyla eklendi/güncellendi');
        setSelectedPriceMaterial('');
        setMaterialPrice('');
        await loadMaterials();
        await loadMaterialPrices();
      } else {
        throw new Error(data.message || 'Fiyat eklenemedi');
      }
    }, 'Fiyat güncelleme');
  };

  // Start editing material
  const startEditMaterial = (material: Material) => {
    setEditingMaterialId(material.id);
    setEditValues({
      ...editValues,
      [`material_${material.id}_name`]: material.name,
      [`material_${material.id}_density`]: material.density?.toString() || ''
    });
  };

  // Cancel editing material
  const cancelEditMaterial = () => {
    setEditingMaterialId(null);
  };

  // Save edited material
  const saveEditedMaterial = async (material: Material) => {
    const newName = editValues[`material_${material.id}_name`];
    const newDensity = editValues[`material_${material.id}_density`];

    if (!newName?.trim()) {
      showError('Malzeme adı gerekli');
      return;
    }

    await performOperationWithCacheRefresh(async () => {
      const updateData = {
        name: newName.trim(),
        density: newDensity ? parseFloat(newDensity) : null
      };

      const { data } = await apiRequest(`/api/materials/${material.id}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
      });

      if (data.success) {
        showSuccess('Malzeme güncellendi');
        setEditingMaterialId(null);
        await loadMaterials();
      } else {
        throw new Error(data.message || 'Malzeme güncellenemedi');
      }
    }, 'Malzeme güncelleme');
  };

  // Start editing price
  const startEditPrice = (price: MaterialPrice) => {
    setEditingPriceId(price.id);
    setEditValues({
      ...editValues,
      [`price_${price.id}`]: price.price.toString()
    });
  };

  // Cancel editing price
  const cancelEditPrice = () => {
    setEditingPriceId(null);
  };

  // Save edited price
  const saveEditedPrice = async (price: MaterialPrice) => {
    const newPrice = editValues[`price_${price.id}`];

    if (!newPrice) {
      showError('Fiyat gerekli');
      return;
    }

    await performOperationWithCacheRefresh(async () => {
      const { data } = await apiRequest(`/api/materials/${price.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          price_per_kg: parseFloat(newPrice)
        })
      });

      if (data.success) {
        showSuccess('Fiyat güncellendi');
        setEditingPriceId(null);
        await loadMaterials();
        await loadMaterialPrices();
      } else {
        throw new Error(data.message || 'Fiyat güncellenemedi');
      }
    }, 'Fiyat güncelleme');
  };

  const renderAliases = (rowData: Material) => {
    const aliases = rowData.aliases || [];
    return (
      <div className={classes.aliasContainer}>
        {aliases.map((alias, index) => (
          <span
            key={index}
            className={classes.aliasChip}
            onClick={() => handleDeleteAlias(rowData.id, alias)}
            title='Silmek için tıklayın'>
            {alias}
            <span className={classes.aliasDelete}>×</span>
          </span>
        ))}
      </div>
    );
  };

  const handleDeleteAlias = async (materialId: string, alias: string) => {
    try {
      const { data } = await apiRequest(
        `/api/materials/${materialId}/aliases/${encodeURIComponent(alias)}`,
        {
          method: 'DELETE'
        }
      );

      if (data.success) {
        showSuccess('Alias silindi');
        await loadMaterials();
        await handleCacheRefresh();
      } else {
        showError(data.message || 'Alias silinemedi');
      }
    } catch (error) {
      showError('Alias silinirken hata oluştu');
    }
  };

  const handleDeleteMaterial = (material: Material) => {
    confirmDialog({
      message: `"${material.name}" malzemesini silmek istediğinize emin misiniz?`,
      header: 'Silme Onayı',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        await performOperationWithCacheRefresh(async () => {
          const { data } = await apiRequest(`/api/materials/${material.id}`, {
            method: 'DELETE'
          });

          if (data.success) {
            showSuccess('Malzeme silindi');
            await loadMaterials();
          } else {
            throw new Error(data.message || 'Malzeme silinemedi');
          }
        }, 'Malzeme silme');
      }
    });
  };

  const handleDeletePrice = (priceItem: MaterialPrice) => {
    confirmDialog({
      message: `"${priceItem.material_name}" fiyatını silmek istediğinize emin misiniz?`,
      header: 'Silme Onayı',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        await performOperationWithCacheRefresh(async () => {
          const { data } = await apiRequest(`/api/materials/${priceItem.id}`, {
            method: 'PUT',
            body: JSON.stringify({
              price_per_kg: null
            })
          });

          if (data.success) {
            showSuccess('Fiyat silindi');
            await loadMaterials();
            await loadMaterialPrices();
          } else {
            throw new Error(data.message || 'Fiyat silinemedi');
          }
        }, 'Fiyat silme');
      }
    });
  };

  const materialOptions: DropdownOption[] = materials.map((material) => ({
    label: material.name,
    value: material.id
  }));

  const materialNameOptions: DropdownOption[] = materials.map((material) => ({
    label: material.name,
    value: material.name
  }));

  // Material Cards Render
  const renderMaterialCards = () => {
    return materials.map((material) => {
      const isEditing = editingMaterialId === material.id;

      return (
        <div
          key={material.id}
          className={classes.materialCard}>
          <div className={classes.materialHeader}>
            {isEditing ? (
              <input
                type='text'
                value={editValues[`material_${material.id}_name`] || ''}
                onChange={(e) =>
                  setEditValues({
                    ...editValues,
                    [`material_${material.id}_name`]: e.target.value
                  })
                }
                className={classes.inlineEditInput}
                autoFocus
              />
            ) : (
              <h4 className={classes.materialName}>{material.name}</h4>
            )}
            <div className={classes.materialActions}>
              {isEditing ? (
                <>
                  <button
                    className={`${classes.iconButton} ${classes.saveButton}`}
                    onClick={() => saveEditedMaterial(material)}
                    title='Kaydet'>
                    <i className='pi pi-check'></i>
                  </button>
                  <button
                    className={`${classes.iconButton} ${classes.cancelButton}`}
                    onClick={cancelEditMaterial}
                    title='İptal'>
                    <i className='pi pi-times'></i>
                  </button>
                </>
              ) : (
                <>
                  <button
                    className={classes.iconButton}
                    onClick={() => startEditMaterial(material)}
                    title='Düzenle'>
                    <i className='pi pi-pencil'></i>
                  </button>
                  <button
                    className={`${classes.iconButton} ${classes.deleteButton}`}
                    onClick={() => handleDeleteMaterial(material)}
                    title='Sil'>
                    <i className='pi pi-trash'></i>
                  </button>
                </>
              )}
            </div>
          </div>

          <div className={classes.materialInfo}>
            <div className={classes.infoRow}>
              <span className={classes.infoLabel}>Özkütle:</span>
              {isEditing ? (
                <input
                  type='number'
                  value={editValues[`material_${material.id}_density`] || ''}
                  onChange={(e) =>
                    setEditValues({
                      ...editValues,
                      [`material_${material.id}_density`]: e.target.value
                    })
                  }
                  placeholder='0.00'
                  step='0.01'
                  className={classes.inlineEditInputSmall}
                />
              ) : (
                <span className={classes.infoValue}>
                  {material.density
                    ? `${material.density.toFixed(2)} g/cm³`
                    : '-'}
                </span>
              )}
            </div>
            <div className={classes.infoRow}>
              <span className={classes.infoLabel}>Fiyat:</span>
              <span className={classes.infoValue}>
                {material.price_per_kg
                  ? `${material.price_per_kg.toFixed(2)}/kg`
                  : '-'}
              </span>
            </div>
          </div>

          {material.aliases && material.aliases.length > 0 && (
            <div className={classes.materialAliases}>
              <span className={classes.aliasLabel}>Aliaslar:</span>
              {renderAliases(material)}
            </div>
          )}
        </div>
      );
    });
  };

  // Price Cards Render
  const renderPriceCards = () => {
    return materialPrices.map((price) => {
      const isEditing = editingPriceId === price.id;

      return (
        <div
          key={price.id}
          className={classes.priceCard}>
          <div className={classes.priceHeader}>
            <h4 className={classes.priceMaterialName}>{price.material_name}</h4>
            <div className={classes.priceHeaderRight}>
              {isEditing ? (
                <div className={classes.priceEditContainer}>
                  <span className={classes.dollarSign}>$</span>
                  <input
                    type='number'
                    value={editValues[`price_${price.id}`] || ''}
                    onChange={(e) =>
                      setEditValues({
                        ...editValues,
                        [`price_${price.id}`]: e.target.value
                      })
                    }
                    step='0.01'
                    className={classes.priceEditInput}
                    autoFocus
                  />
                  <span className={classes.priceUnit}>/kg</span>
                </div>
              ) : (
                <div className={classes.priceValue}>
                  ${price.price.toFixed(2)}
                  <span className={classes.priceUnit}>/kg</span>
                </div>
              )}
              <div className={classes.priceCardActions}>
                {isEditing ? (
                  <>
                    <button
                      className={`${classes.iconButton} ${classes.saveButton}`}
                      onClick={() => saveEditedPrice(price)}
                      title='Kaydet'>
                      <i className='pi pi-check'></i>
                    </button>
                    <button
                      className={`${classes.iconButton} ${classes.cancelButton}`}
                      onClick={cancelEditPrice}
                      title='İptal'>
                      <i className='pi pi-times'></i>
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className={classes.iconButton}
                      onClick={() => startEditPrice(price)}
                      title='Düzenle'>
                      <i className='pi pi-pencil'></i>
                    </button>
                    <button
                      className={`${classes.iconButton} ${classes.deleteButton}`}
                      onClick={() => handleDeletePrice(price)}
                      title='Sil'>
                      <i className='pi pi-trash'></i>
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {price.density && (
            <div className={classes.priceInfo}>
              <div className={classes.densityInfo}>
                <i className='pi pi-info-circle'></i>
                Özkütle: {price.density.toFixed(2)} g/cm³
              </div>
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div className={classes.container}>
      <Toast ref={toast} />
      <ConfirmDialog />

      {/* Header Section */}
      <div className={classes.headerSection}>
        <h1 className={classes.pageTitle}>⚙️ Parametre Düzenleme</h1>
        <p className={classes.pageDescription}>
          Malzeme tanımlarını ve fiyatlarını yönetin. Yaptığınız değişiklikler
          analiz sistemine otomatik yansıtılır.
        </p>

        {/* Cache Management */}
        <div className={classes.cacheManagement}>
          <button
            className={`${classes.cacheButton} ${
              refreshingCache ? classes.cacheButtonLoading : ''
            }`}
            onClick={handleCacheRefresh}
            disabled={refreshingCache}>
            <i
              className={`pi ${
                refreshingCache ? 'pi-spin pi-spinner' : 'pi-refresh'
              }`}></i>
            {refreshingCache ? 'Yenileniyor...' : 'Cache Yenile'}
          </button>
          {lastCacheRefresh && (
            <span className={classes.cacheInfo}>
              Son yenileme: {lastCacheRefresh.toLocaleString('tr-TR')}
            </span>
          )}
        </div>
      </div>

      {/* Main Content - Split Layout */}
      <div className={classes.mainContent}>
        {/* Left Panel - Forms */}
        <div className={classes.leftPanel}>
          <div className={classes.panelHeader}>
            <h3>📝 Malzeme İşlemleri</h3>
            <p>Yeni malzeme ekleyin veya mevcut malzemelere alias tanımlayın</p>
          </div>

          {/* New Material Form */}
          <div className={classes.formCard}>
            <h4>🆕 Yeni Malzeme Ekle</h4>
            <div className={classes.formFields}>
              <div className={classes.fieldGroup}>
                <label>
                  Malzeme Adı <span className={classes.required}>*</span>
                </label>
                <input
                  type='text'
                  value={newMaterialName}
                  onChange={(e) => setNewMaterialName(e.target.value)}
                  placeholder='Örn: Alüminyum'
                  className={classes.inputField}
                />
              </div>

              <div className={classes.fieldGroup}>
                <label>Aliaslar</label>
                <input
                  type='text'
                  value={newMaterialAliases}
                  onChange={(e) => setNewMaterialAliases(e.target.value)}
                  placeholder='Virgülle ayırın: AL, Aluminum'
                  className={classes.inputField}
                />
              </div>

              <div className={classes.fieldGroup}>
                <label>Özkütle (g/cm³)</label>
                <input
                  type='number'
                  value={newMaterialDensity}
                  onChange={(e) => setNewMaterialDensity(e.target.value)}
                  placeholder='2.70'
                  step='0.01'
                  className={classes.inputField}
                />
              </div>

              <button
                className={`${classes.submitButton} ${
                  !newMaterialName.trim() ? classes.submitButtonDisabled : ''
                }`}
                onClick={handleAddNewMaterial}
                disabled={!newMaterialName.trim()}>
                <i className='pi pi-plus'></i> Malzeme Ekle
              </button>
            </div>
          </div>

          {/* Add Alias Form */}
          <div className={classes.formCard}>
            <h4>🏷️ Alias Ekle</h4>
            <div className={classes.formFields}>
              <div className={classes.fieldGroup}>
                <label>
                  Malzeme Seçin <span className={classes.required}>*</span>
                </label>
                <Dropdown
                  value={selectedMaterial}
                  onChange={(e) => setSelectedMaterial(e.value)}
                  options={materialOptions}
                  placeholder='Malzeme seçin'
                  className={classes.dropdownField}
                  panelClassName={classes.dropdownPanel}
                />
              </div>

              <div className={classes.fieldGroup}>
                <label>
                  Aliaslar <span className={classes.required}>*</span>
                </label>
                <input
                  type='text'
                  value={newAliases}
                  onChange={(e) => setNewAliases(e.target.value)}
                  placeholder='Virgülle ayırın'
                  className={classes.inputField}
                />
              </div>

              <button
                className={`${classes.submitButton} ${
                  !selectedMaterial || !newAliases.trim()
                    ? classes.submitButtonDisabled
                    : ''
                }`}
                onClick={handleAddAlias}
                disabled={!selectedMaterial || !newAliases.trim()}>
                <i className='pi pi-plus'></i> Alias Ekle
              </button>
            </div>
          </div>

          {/* Price Form */}
          <div className={classes.formCard}>
            <h4>💰 Fiyat Güncelle</h4>
            <div className={classes.formFields}>
              <div className={classes.fieldGroup}>
                <label>
                  Malzeme <span className={classes.required}>*</span>
                </label>
                <Dropdown
                  value={selectedPriceMaterial}
                  onChange={(e) => setSelectedPriceMaterial(e.value)}
                  options={materialNameOptions}
                  placeholder='Malzeme seçin'
                  className={classes.dropdownField}
                  panelClassName={classes.dropdownPanel}
                />
              </div>

              <div className={classes.fieldGroup}>
                <label>
                  Fiyat (USD/kg) <span className={classes.required}>*</span>
                </label>
                <input
                  type='number'
                  value={materialPrice}
                  onChange={(e) => setMaterialPrice(e.target.value)}
                  placeholder='0.00'
                  step='0.01'
                  className={classes.inputField}
                />
              </div>

              <button
                className={`${classes.submitButton} ${
                  !selectedPriceMaterial || !materialPrice
                    ? classes.submitButtonDisabled
                    : ''
                }`}
                onClick={handleAddMaterialPrice}
                disabled={!selectedPriceMaterial || !materialPrice}>
                <i className='pi pi-dollar'></i> Fiyat Güncelle
              </button>
            </div>
          </div>

          {/* Info Panel */}
          <div className={classes.infoPanel}>
            <i className='pi pi-info-circle'></i>
            <p>
              <strong>Önemli:</strong> Malzeme değişikliklerinden sonra "Cache
              Yenile" butonuna tıklayın. Bu sayede analiz sistemi yeni
              malzemeleri tanımaya başlar.
            </p>
          </div>
        </div>

        {/* Right Panel - Lists */}
        <div className={classes.rightPanel}>
          {/* Tab Navigation */}
          <div className={classes.tabNavigation}>
            <button
              className={`${classes.tabButton} ${
                activeTab === 'materials' ? classes.tabButtonActive : ''
              }`}
              onClick={() => setActiveTab('materials')}>
              📋 Malzemeler ({materials.length})
            </button>
            <button
              className={`${classes.tabButton} ${
                activeTab === 'prices' ? classes.tabButtonActive : ''
              }`}
              onClick={() => setActiveTab('prices')}>
              💰 Fiyatlar ({materialPrices.length})
            </button>
          </div>

          {/* Content Area */}
          <div className={classes.contentArea}>
            {loading ? (
              <div className={classes.loadingState}>
                <i
                  className='pi pi-spin pi-spinner'
                  style={{ fontSize: '2rem' }}></i>
                <p>Yükleniyor...</p>
              </div>
            ) : (
              <>
                {activeTab === 'materials' && (
                  <div className={classes.cardGrid}>
                    {materials.length === 0 ? (
                      <div className={classes.emptyState}>
                        <span className={classes.emptyIcon}>📦</span>
                        <p>Henüz malzeme eklenmemiş</p>
                        <p className={classes.emptySubtext}>
                          Sol panelden yeni malzeme ekleyebilirsiniz
                        </p>
                      </div>
                    ) : (
                      renderMaterialCards()
                    )}
                  </div>
                )}

                {activeTab === 'prices' && (
                  <div className={classes.priceGrid}>
                    {materialPrices.length === 0 ? (
                      <div className={classes.emptyState}>
                        <span className={classes.emptyIcon}>💸</span>
                        <p>Henüz fiyat bilgisi yok</p>
                        <p className={classes.emptySubtext}>
                          Sol panelden malzeme fiyatları ekleyebilirsiniz
                        </p>
                      </div>
                    ) : (
                      renderPriceCards()
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Dialog'ları kaldırıyoruz çünkü artık inline düzenleme var */}
    </div>
  );
};
