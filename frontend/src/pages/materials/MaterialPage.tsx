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

export const MaterialPage = () => {
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

  // API Helper function
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
      // Fiyat bilgilerini materials koleksiyonundan al (price_per_kg field'ı olan)
      const { data } = await apiRequest('/api/materials?limit=1000');
      
      if (data.success) {
        // Sadece fiyat bilgisi olan malzemeleri filtrele
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

  // Alias ekleme
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

  // Yeni malzeme ekleme
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

  // Malzeme fiyatı ekleme/güncelleme - Materials koleksiyonundaki price_per_kg field'ını güncelle
  const handleAddMaterialPrice = async () => {
    if (!selectedPriceMaterial || !materialPrice) {
      showError('Malzeme seçin ve fiyat girin');
      return;
    }

    try {
      // İlk olarak malzeme adına göre ID'yi bul
      const selectedMaterial = materials.find(m => m.name === selectedPriceMaterial);
      if (!selectedMaterial) {
        showError('Seçilen malzeme bulunamadı');
        return;
      }

      // Material'ın price_per_kg field'ını güncelle
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
        // Her iki listeyi de yenile
        loadMaterials();
        loadMaterialPrices();
      } else {
        showError(data.message || 'Fiyat eklenemedi');
      }
    } catch (error) {
      showError('Fiyat eklenirken hata oluştu');
    }
  };

  // Alias silme
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

  // Malzeme silme
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

  // Malzeme düzenleme
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

  // Fiyat düzenleme - Materials koleksiyonundaki price_per_kg field'ını güncelle
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
      // Material ID'si priceItem.id'de
      const { data } = await apiRequest(`/api/materials/${editingPrice.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          price_per_kg: parseFloat(editPriceValue)
        })
      });

      if (data.success) {
        showSuccess('Fiyat güncellendi');
        setEditPriceDialog(false);
        // Her iki listeyi de yenile
        loadMaterials();
        loadMaterialPrices();
      } else {
        showError(data.message || 'Fiyat güncellenemedi');
      }
    } catch (error) {
      showError('Fiyat güncellenirken hata oluştu');
    }
  };

  // Fiyat silme - Materials koleksiyonundaki price_per_kg field'ını null yap
  const handleDeletePrice = (priceItem: MaterialPrice) => {
    confirmDialog({
      message: `"${priceItem.material_name}" fiyatını silmek istediğinize emin misiniz?`,
      header: 'Silme Onayı',
      icon: 'pi pi-exclamation-triangle',
      accept: async () => {
        try {
          // Material'ın price_per_kg field'ını null yap
          const { data } = await apiRequest(`/api/materials/${priceItem.id}`, {
            method: 'PUT',
            body: JSON.stringify({
              price_per_kg: null
            })
          });

          if (data.success) {
            showSuccess('Fiyat silindi');
            // Her iki listeyi de yenile
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

  // Render functions
  const renderAliases = (rowData: Material) => {
    const aliases = rowData.aliases || [];
    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
        {aliases.map((alias, index) => (
          <Badge
            key={index}
            value={alias}
            severity="secondary"
            style={{ cursor: 'pointer' }}
            onClick={() => handleDeleteAlias(rowData.id, alias)}
          />
        ))}
      </div>
    );
  };

  const renderActions = (rowData: Material) => {
    return (
      <div style={{ display: 'flex', gap: '8px' }}>
        <Button
          icon="pi pi-pencil"
          size="small"
          severity="info"
          outlined
          onClick={() => openEditMaterial(rowData)}
          tooltip="Düzenle"
        />
        <Button
          icon="pi pi-trash"
          size="small"
          severity="danger"
          outlined
          onClick={() => handleDeleteMaterial(rowData)}
          tooltip="Sil"
        />
      </div>
    );
  };

  const renderPriceActions = (rowData: MaterialPrice) => {
    return (
      <div style={{ display: 'flex', gap: '8px' }}>
        <Button
          icon="pi pi-pencil"
          size="small"
          severity="info"
          outlined
          onClick={() => openEditPrice(rowData)}
          tooltip="Düzenle"
        />
        <Button
          icon="pi pi-trash"
          size="small"
          severity="danger"
          outlined
          onClick={() => handleDeletePrice(rowData)}
          tooltip="Sil"
        />
      </div>
    );
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
    <div style={{ padding: '2rem' }}>
      <Toast ref={toast} />
      <ConfirmDialog />
      
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1>⚙️ Parametre Düzenleme</h1>
      </div>

      {/* Alias Ekleme Kartı */}
      <Card title="Mevcut Malzemeye Alias Ekle" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '1rem', alignItems: 'end' }}>
          <div>
            <label htmlFor="material-select" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Malzeme Seçin
            </label>
            <Dropdown
              id="material-select"
              value={selectedMaterial}
              onChange={(e) => setSelectedMaterial(e.value)}
              options={materialOptions}
              placeholder="Malzeme Seçin"
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label htmlFor="aliases-input" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Alias (virgülle ayır)
            </label>
            <InputText
              id="aliases-input"
              value={newAliases}
              onChange={(e) => setNewAliases(e.target.value)}
              placeholder="Alias (virgülle ayır)"
              style={{ width: '100%' }}
            />
          </div>
          <Button
            label="Alias Ekle"
            onClick={handleAddAlias}
            disabled={!selectedMaterial || !newAliases.trim()}
          />
        </div>
      </Card>

      {/* Yeni Malzeme Ekleme Kartı */}
      <Card title="🆕 Yeni Malzeme Ekle" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 1fr auto', gap: '1rem', alignItems: 'end' }}>
          <div>
            <label htmlFor="new-material-name" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Yeni Malzeme Adı *
            </label>
            <InputText
              id="new-material-name"
              value={newMaterialName}
              onChange={(e) => setNewMaterialName(e.target.value)}
              placeholder="Yeni Malzeme Adı"
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label htmlFor="new-material-aliases" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Alias (virgülle ayır)
            </label>
            <InputText
              id="new-material-aliases"
              value={newMaterialAliases}
              onChange={(e) => setNewMaterialAliases(e.target.value)}
              placeholder="Alias (virgülle ayır)"
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label htmlFor="new-material-density" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Özkütle (g/cm³)
            </label>
            <InputText
              id="new-material-density"
              value={newMaterialDensity}
              onChange={(e) => setNewMaterialDensity(e.target.value)}
              placeholder="Özkütle"
              type="number"
              step="0.01"
              style={{ width: '100%' }}
            />
          </div>
          <Button
            label="Ekle"
            severity="success"
            onClick={handleAddNewMaterial}
            disabled={!newMaterialName.trim()}
          />
        </div>
      </Card>

      {/* Mevcut Malzemeler Tablosu */}
      <Card title="📋 Mevcut Malzemeler" style={{ marginBottom: '2rem' }}>
        <DataTable
          value={materials}
          loading={loading}
          paginator
          rows={10}
          emptyMessage="Henüz malzeme eklenmedi."
          style={{ marginTop: '1rem' }}
        >
          <Column field="id" header="ID" style={{ width: '100px' }} />
          <Column field="name" header="Malzeme Adı" />
          <Column body={renderAliases} header="Alias'lar" style={{ maxWidth: '300px' }} />
          <Column 
            field="density" 
            header="Özkütle (g/cm³)" 
            style={{ width: '120px' }}
            body={(rowData: Material) => rowData.density?.toFixed(2) || '-'}
          />
          <Column 
            field="price_per_kg" 
            header="Fiyat (USD/kg)" 
            style={{ width: '120px' }}
            body={(rowData: Material) => rowData.price_per_kg ? `${rowData.price_per_kg.toFixed(2)}` : '-'}
          />
          <Column body={renderActions} header="İşlemler" style={{ width: '120px' }} />
        </DataTable>
      </Card>

      {/* Malzeme Fiyatları Kartı */}
      <Card title="💰 Malzeme KG Ücretleri (USD)">
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: '1rem', alignItems: 'end', marginBottom: '1rem' }}>
          <div>
            <label htmlFor="price-material-select" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Malzeme Seçin
            </label>
            <Dropdown
              id="price-material-select"
              value={selectedPriceMaterial}
              onChange={(e) => setSelectedPriceMaterial(e.value)}
              options={materialNameOptions}
              placeholder="Malzeme Seçin"
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label htmlFor="material-price" style={{ display: 'block', marginBottom: '0.5rem' }}>
              USD/kg
            </label>
            <InputText
              id="material-price"
              value={materialPrice}
              onChange={(e) => setMaterialPrice(e.target.value)}
              placeholder="USD/kg"
              type="number"
              step="0.01"
              style={{ width: '100%' }}
            />
          </div>
          <Button
            label="Ekle / Güncelle"
            severity="success"
            onClick={handleAddMaterialPrice}
            disabled={!selectedPriceMaterial || !materialPrice}
          />
        </div>

        <DataTable
          value={materialPrices}
          emptyMessage="Henüz ücret bilgisi girilmedi."
          paginator
          rows={5}
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
          />
          <Column body={renderPriceActions} header="İşlemler" style={{ width: '120px' }} />
        </DataTable>
      </Card>

      {/* Malzeme Düzenleme Dialog */}
      <Dialog
        header="Malzeme Düzenle"
        visible={editMaterialDialog}
        style={{ width: '400px' }}
        onHide={() => setEditMaterialDialog(false)}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label htmlFor="edit-name" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Malzeme Adı *
            </label>
            <InputText
              id="edit-name"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label htmlFor="edit-density" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Özkütle (g/cm³)
            </label>
            <InputText
              id="edit-density"
              value={editDensity}
              onChange={(e) => setEditDensity(e.target.value)}
              type="number"
              step="0.01"
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <Button
              label="İptal"
              severity="secondary"
              outlined
              onClick={() => setEditMaterialDialog(false)}
            />
            <Button
              label="Güncelle"
              onClick={handleUpdateMaterial}
            />
          </div>
        </div>
      </Dialog>

      {/* Fiyat Düzenleme Dialog */}
      <Dialog
        header="Fiyat Düzenle"
        visible={editPriceDialog}
        style={{ width: '300px' }}
        onHide={() => setEditPriceDialog(false)}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label htmlFor="edit-price" style={{ display: 'block', marginBottom: '0.5rem' }}>
              Fiyat (USD/kg) *
            </label>
            <InputText
              id="edit-price"
              value={editPriceValue}
              onChange={(e) => setEditPriceValue(e.target.value)}
              type="number"
              step="0.01"
              style={{ width: '100%' }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <Button
              label="İptal"
              severity="secondary"
              outlined
              onClick={() => setEditPriceDialog(false)}
            />
            <Button
              label="Güncelle"
              onClick={handleUpdatePrice}
            />
          </div>
        </div>
      </Dialog>
    </div>
  );
};