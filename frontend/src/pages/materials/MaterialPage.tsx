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
import { MaterialPageStyles } from './MaterialPage.styles'; // Import styles

// Types (same as before)
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

export const MaterialPage = () => {
  const classes = MaterialPageStyles(); // Use styles
  
  // State variables (same as before)
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialPrices, setMaterialPrices] = useState<MaterialPrice[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<string>('');
  const [newAliases, setNewAliases] = useState('');
  
  // Yeni malzeme ekleme
  const [newMaterialName, setNewMaterialName] = useState('');
  const [newMaterialAliases, setNewMaterialAliases] = useState('');
  const [newMaterialDensity, setNewMaterialDensity] = useState('');
  
  // Fiyat ekleme
  const [selectedPriceMaterial, setSelectedPriceMaterial] = useState<string>('');
  const [materialPrice, setMaterialPrice] = useState('');
  
  // Edit dialogs
  const [editMaterialDialog, setEditMaterialDialog] = useState(false);
  const [editingMaterial, setEditingMaterial] = useState<Material | null>(null);
  const [editName, setEditName] = useState('');
  const [editDensity, setEditDensity] = useState('');
  
  const [editPriceDialog, setEditPriceDialog] = useState(false);
  const [editingPrice, setEditingPrice] = useState<MaterialPrice | null>(null);
  const [editPriceValue, setEditPriceValue] = useState('');

  const toast = React.useRef<Toast>(null);

  // API Helper function (same as before)
  const apiRequest = async (endpoint: string, options: RequestInit = {}) => {
    const defaultOptions: RequestInit = {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        'Content-Type': 'application/json'
      }
    };

    const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:5050'}${endpoint}`, {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers
      }
    });

    const data = await response.json();
    return { response, data };
  };

  // All the existing functions remain the same, just updating the render part
  useEffect(() => {
    loadMaterials();
    loadMaterialPrices();
  }, []);

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
        const pricesData = data.materials
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
    toast.current?.show({ severity: 'success', summary: 'Başarılı', detail: message, life: 3000 });
  };

  const showError = (message: string) => {
    toast.current?.show({ severity: 'error', summary: 'Hata', detail: message, life: 3000 });
  };

  // All existing handler functions remain the same...
  const handleAddAlias = async () => {
    if (!selectedMaterial || !newAliases.trim()) {
      showError('Malzeme seçin ve alias girin');
      return;
    }

    try {
      const aliasArray = newAliases.split(',').map(alias => alias.trim()).filter(alias => alias);
      
      const { data } = await apiRequest(`/api/materials/${selectedMaterial}/aliases`, {
        method: 'POST',
        body: JSON.stringify({ aliases: aliasArray })
      });

      if (data.success) {
        showSuccess('Alias başarıyla eklendi');
        setSelectedMaterial('');
        setNewAliases('');
        loadMaterials();
      } else {
        showError(data.message || 'Alias eklenemedi');
      }
    } catch (error) {
      showError('Alias eklenirken hata oluştu');
    }
  };

  const handleAddNewMaterial = async () => {
    if (!newMaterialName.trim()) {
      showError('Malzeme adı gerekli');
      return;
    }

    try {
      const materialData = {
        name: newMaterialName.trim(),
        aliases: newMaterialAliases ? newMaterialAliases.split(',').map(alias => alias.trim()).filter(alias => alias) : [],
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
        loadMaterials();
      } else {
        showError(data.message || 'Malzeme eklenemedi');
      }
    } catch (error) {
      showError('Malzeme eklenirken hata oluştu');
    }
  };

  const handleAddMaterialPrice = async () => {
    if (!selectedPriceMaterial || !materialPrice) {
      showError('Malzeme seçin ve fiyat girin');
      return;
    }

    try {
      const selectedMaterial = materials.find(m => m.name === selectedPriceMaterial);
      if (!selectedMaterial) {
        showError('Seçilen malzeme bulunamadı');
        return;
      }

      const { data } = await apiRequest(`/api/materials/${selectedMaterial.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          price_per_kg: parseFloat(materialPrice)
        })
      });

      if (data.success) {
        showSuccess('Fiyat başarıyla eklendi/güncellendi');
        setSelectedPriceMaterial('');
        setMaterialPrice('');
        loadMaterials();
        loadMaterialPrices();
      } else {
        showError(data.message || 'Fiyat eklenemedi');
      }
    } catch (error) {
      showError('Fiyat eklenirken hata oluştu');
    }
  };

  // Render functions with responsive updates
  const renderAliases = (rowData: Material) => {
    const aliases = rowData.aliases || [];
    return (
      <div className={classes.badgeContainer}>
        {aliases.map((alias, index) => (
          <Badge
            key={index}
            value={alias}
            severity="secondary"
            onClick={() => handleDeleteAlias(rowData.id, alias)}
            title="Silmek için tıklayın"
          />
        ))}
      </div>
    );
  };

  const renderActions = (rowData: Material) => {
    return (
      <div className={classes.actionButtons}>
        <Button
          icon="pi pi-pencil"
          size="small"
          severity="info"
          outlined
          onClick={() => openEditMaterial(rowData)}
          tooltip="Düzenle"
          className={classes.responsiveButton}
        />
        <Button
          icon="pi pi-trash"
          size="small"
          severity="danger"
          outlined
          onClick={() => handleDeleteMaterial(rowData)}
          tooltip="Sil"
          className={classes.responsiveButton}
        />
      </div>
    );
  };

  const renderPriceActions = (rowData: MaterialPrice) => {
    return (
      <div className={classes.actionButtons}>
        <Button
          icon="pi pi-pencil"
          size="small"
          severity="info"
          outlined
          onClick={() => openEditPrice(rowData)}
          tooltip="Düzenle"
          className={classes.responsiveButton}
        />
        <Button
          icon="pi pi-trash"
          size="small"
          severity="danger"
          outlined
          onClick={() => handleDeletePrice(rowData)}
          tooltip="Sil"
          className={classes.responsiveButton}
        />
      </div>
    );
  };

  // More functions... (keeping them the same but adding to the component)
  const handleDeleteAlias = async (materialId: string, alias: string) => {
    try {
      const { data } = await apiRequest(`/api/materials/${materialId}/aliases/${encodeURIComponent(alias)}`, {
        method: 'DELETE'
      });

      if (data.success) {
        showSuccess('Alias silindi');
        loadMaterials();
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
        try {
          const { data } = await apiRequest(`/api/materials/${material.id}`, {
            method: 'DELETE'
          });

          if (data.success) {
            showSuccess('Malzeme silindi');
            loadMaterials();
          } else {
            showError(data.message || 'Malzeme silinemedi');
          }
        } catch (error) {
          showError('Malzeme silinirken hata oluştu');
        }
      }
    });
  };

  const openEditMaterial = (material: Material) => {
    setEditingMaterial(material);
    setEditName(material.name);
    setEditDensity(material.density?.toString() || '');
    setEditMaterialDialog(true);
  };

  const handleUpdateMaterial = async () => {
    if (!editName.trim()) {
      showError('Malzeme adı gerekli');
      return;
    }

    if (!editingMaterial) return;

    try {
      const updateData = {
        name: editName.trim(),
        density: editDensity ? parseFloat(editDensity) : null
      };

      const { data } = await apiRequest(`/api/materials/${editingMaterial.id}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
      });

      if (data.success) {
        showSuccess('Malzeme güncellendi');
        setEditMaterialDialog(false);
        loadMaterials();
      } else {
        showError(data.message || 'Malzeme güncellenemedi');
      }
    } catch (error) {
      showError('Malzeme güncellenirken hata oluştu');
    }
  };

  const openEditPrice = (priceItem: MaterialPrice) => {
    setEditingPrice(priceItem);
    setEditPriceValue(priceItem.price.toString());
    setEditPriceDialog(true);
  };

  const handleUpdatePrice = async () => {
    if (!editPriceValue || !editingPrice) {
      showError('Fiyat gerekli');
      return;
    }

    try {
      const { data } = await apiRequest(`/api/materials/${editingPrice.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          price_per_kg: parseFloat(editPriceValue)
        })
      });

      if (data.success) {
        showSuccess('Fiyat güncellendi');
        setEditPriceDialog(false);
        loadMaterials();
        loadMaterialPrices();
      } else {
        showError(data.message || 'Fiyat güncellenemedi');
      }
    } catch (error) {
      showError('Fiyat güncellenirken hata oluştu');
    }
  };

  const handleDeletePrice = (priceItem: MaterialPrice) => {
    confirmDialog({
      message: `"${priceItem.material_name}" fiyatını silmek istediğinize emin misiniz?`,
      header: 'Silme Onayı',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          const { data } = await apiRequest(`/api/materials/${priceItem.id}`, {
            method: 'PUT',
            body: JSON.stringify({
              price_per_kg: null
            })
          });

          if (data.success) {
            showSuccess('Fiyat silindi');
            loadMaterials();
            loadMaterialPrices();
          } else {
            showError(data.message || 'Fiyat silinemedi');
          }
        } catch (error) {
          showError('Fiyat silinirken hata oluştu');
        }
      }
    });
  };

  const materialOptions: DropdownOption[] = materials.map(material => ({
    label: material.name,
    value: material.id
  }));

  const materialNameOptions: DropdownOption[] = materials.map(material => ({
    label: material.name,
    value: material.name
  }));

  return (
    <div className={classes.container}>
      <Toast ref={toast} />
      <ConfirmDialog />
      
      <h1 className={classes.pageTitle}>⚙️ Parametre Düzenleme</h1>

      {/* Alias Ekleme Kartı */}
      <div className={classes.cardContainer}>
        <Card title="Mevcut Malzemeye Alias Ekle">
          <div className={`${classes.formGrid} grid-3`}>
            <div className={classes.fieldWrapper}>
              <label htmlFor="material-select">
                Malzeme Seçin <span className="required">*</span>
              </label>
              <Dropdown
                id="material-select"
                value={selectedMaterial}
                onChange={(e) => setSelectedMaterial(e.value)}
                options={materialOptions}
                placeholder="Malzeme Seçin"
                className="w-full"
              />
            </div>
            <div className={classes.fieldWrapper}>
              <label htmlFor="aliases-input">
                Alias (virgülle ayır) <span className="required">*</span>
              </label>
              <InputText
                id="aliases-input"
                value={newAliases}
                onChange={(e) => setNewAliases(e.target.value)}
                placeholder="Alias (virgülle ayır)"
                className="w-full"
              />
            </div>
            <Button
              label="Alias Ekle"
              onClick={handleAddAlias}
              disabled={!selectedMaterial || !newAliases.trim()}
              className={classes.responsiveButton}
            />
          </div>
        </Card>
      </div>

      {/* Yeni Malzeme Ekleme Kartı */}
      <div className={classes.cardContainer}>
        <Card title="🆕 Yeni Malzeme Ekle">
          <div className={`${classes.formGrid} grid-4`}>
            <div className={classes.fieldWrapper}>
              <label htmlFor="new-material-name">
                Yeni Malzeme Adı <span className="required">*</span>
              </label>
              <InputText
                id="new-material-name"
                value={newMaterialName}
                onChange={(e) => setNewMaterialName(e.target.value)}
                placeholder="Yeni Malzeme Adı"
                className="w-full"
              />
            </div>
            <div className={classes.fieldWrapper}>
              <label htmlFor="new-material-aliases">
                Alias (virgülle ayır)
              </label>
              <InputText
                id="new-material-aliases"
                value={newMaterialAliases}
                onChange={(e) => setNewMaterialAliases(e.target.value)}
                placeholder="Alias (virgülle ayır)"
                className="w-full"
              />
            </div>
            <div className={classes.fieldWrapper}>
              <label htmlFor="new-material-density">
                Özkütle (g/cm³)
              </label>
              <InputText
                id="new-material-density"
                value={newMaterialDensity}
                onChange={(e) => setNewMaterialDensity(e.target.value)}
                placeholder="Özkütle"
                type="number"
                step="0.01"
                className="w-full"
              />
            </div>
            <Button
              label="Ekle"
              severity="success"
              onClick={handleAddNewMaterial}
              disabled={!newMaterialName.trim()}
              className={classes.responsiveButton}
            />
          </div>
        </Card>
      </div>

      {/* Mevcut Malzemeler Tablosu */}
      <div className={classes.cardContainer}>
        <Card title="📋 Mevcut Malzemeler">
          <div className={classes.tableWrapper}>
            <DataTable
              value={materials}
              loading={loading}
              paginator
              rows={10}
              emptyMessage="Henüz malzeme eklenmedi."
              responsiveLayout="scroll"
            >
              <Column field="id" header="ID" style={{ width: '80px' }} className={classes.hideOnMobile} />
              <Column field="name" header="Malzeme Adı" />
              <Column body={renderAliases} header="Alias'lar" />
              <Column 
                field="density" 
                header="Özkütle"
                style={{ width: '100px' }}
                body={(rowData: Material) => rowData.density?.toFixed(2) || '-'}
                className={classes.hideOnMobile}
              />
              <Column 
                field="price_per_kg" 
                header="Fiyat (USD/kg)" 
                style={{ width: '120px' }}
                body={(rowData: Material) => rowData.price_per_kg ? `${rowData.price_per_kg.toFixed(2)}` : '-'}
                className={classes.hideOnMobile}
              />
              <Column body={renderActions} header="İşlemler" style={{ width: '120px' }} />
            </DataTable>
            <div className={classes.scrollHint}>
              💡 Tabloda kaydırarak tüm sütunları görebilirsiniz
            </div>
          </div>
        </Card>
      </div>

      {/* Malzeme Fiyatları Kartı */}
      <div className={classes.cardContainer}>
        <Card title="💰 Malzeme KG Ücretleri (USD)">
          <div className={`${classes.formGrid} grid-3 ${classes.spacingMedium}`}>
            <div className={classes.fieldWrapper}>
              <label htmlFor="price-material-select">
                Malzeme Seçin <span className="required">*</span>
              </label>
              <Dropdown
                id="price-material-select"
                value={selectedPriceMaterial}
                onChange={(e) => setSelectedPriceMaterial(e.value)}
                options={materialNameOptions}
                placeholder="Malzeme Seçin"
                className="w-full"
              />
            </div>
            <div className={classes.fieldWrapper}>
              <label htmlFor="material-price">
                USD/kg <span className="required">*</span>
              </label>
              <InputText
                id="material-price"
                value={materialPrice}
                onChange={(e) => setMaterialPrice(e.target.value)}
                placeholder="USD/kg"
                type="number"
                step="0.01"
                className="w-full"
              />
            </div>
            <Button
              label="Ekle / Güncelle"
              severity="success"
              onClick={handleAddMaterialPrice}
              disabled={!selectedPriceMaterial || !materialPrice}
              className={classes.responsiveButton}
            />
          </div>

          <div className={classes.tableWrapper}>
            <DataTable
              value={materialPrices}
              emptyMessage="Henüz ücret bilgisi girilmedi."
              paginator
              rows={5}
              responsiveLayout="scroll"
            >
              <Column field="material_name" header="Malzeme" />
              <Column 
                field="price" 
                header="Ücret (USD/kg)" 
                body={(rowData: MaterialPrice) => `${rowData.price?.toFixed(2) || '0.00'}`}
              />
              <Column 
                field="density" 
                header="Özkütle (g/cm³)" 
                body={(rowData: MaterialPrice) => rowData.density?.toFixed(2) || '-'}
                className={classes.hideOnMobile}
              />
              <Column body={renderPriceActions} header="İşlemler" style={{ width: '120px' }} />
            </DataTable>
            <div className={classes.scrollHint}>
              💡 Tabloda kaydırarak tüm sütunları görebilirsiniz
            </div>
          </div>
        </Card>
      </div>

      {/* Malzeme Düzenleme Dialog */}
      <Dialog
        header="Malzeme Düzenle"
        visible={editMaterialDialog}
        className={classes.responsiveDialog}
        onHide={() => setEditMaterialDialog(false)}
      >
        <div className={classes.dialogForm}>
          <div className={classes.fieldWrapper}>
            <label htmlFor="edit-name">
              Malzeme Adı <span className="required">*</span>
            </label>
            <InputText
              id="edit-name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full"
            />
          </div>
          <div className={classes.fieldWrapper}>
            <label htmlFor="edit-density">
              Özkütle (g/cm³)
            </label>
            <InputText
              id="edit-density"
              value={editDensity}
              onChange={(e) => setEditDensity(e.target.value)}
              type="number"
              step="0.01"
              className="w-full"
            />
          </div>
          <div className={classes.dialogButtons}>
            <Button
              label="İptal"
              severity="secondary"
              outlined
              onClick={() => setEditMaterialDialog(false)}
              className={classes.responsiveButton}
            />
            <Button
              label="Güncelle"
              onClick={handleUpdateMaterial}
              className={classes.responsiveButton}
            />
          </div>
        </div>
      </Dialog>

      {/* Fiyat Düzenleme Dialog */}
      <Dialog
        header="Fiyat Düzenle"
        visible={editPriceDialog}
        className={classes.responsiveDialog}
        onHide={() => setEditPriceDialog(false)}
      >
        <div className={classes.dialogForm}>
          <div className={classes.fieldWrapper}>
            <label htmlFor="edit-price">
              Fiyat (USD/kg) <span className="required">*</span>
            </label>
            <InputText
              id="edit-price"
              value={editPriceValue}
              onChange={(e) => setEditPriceValue(e.target.value)}
              type="number"
              step="0.01"
              className="w-full"
            />
          </div>
          <div className={classes.dialogButtons}>
            <Button
              label="İptal"
              severity="secondary"
              outlined
              onClick={() => setEditPriceDialog(false)}
              className={classes.responsiveButton}
            />
            <Button
              label="Güncelle"
              onClick={handleUpdatePrice}
              className={classes.responsiveButton}
            />
          </div>
        </div>
      </Dialog>
    </div>
  );
};