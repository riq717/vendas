const { createApp } = Vue;

createApp({
  data() {
    return {
      vendas: [],
      dashboard: { total_vendas: 0, valor_total: 0 },
      form: {
        produto: '',
        preco: '',
        data: '',
        status: '',
        origem: '',
      },
      editId: null,
      filters: {
        q: '',
        status: '',
        origem: '',
        data_inicio: '',
        data_fim: '',
      },
    };
  },

  watch: {
    filters: {
      deep: true,
      handler() {
        this.fetchVendas();
      },
    },
  },

  mounted() {
    this.fetchVendas();
    this.fetchDashboard();
  },

  methods: {
    async fetchVendas() {
      const params = new URLSearchParams();
      if (this.filters.q) params.append('q', this.filters.q);
      if (this.filters.status) params.append('status', this.filters.status);
      if (this.filters.origem) params.append('origem', this.filters.origem);
      if (this.filters.data_inicio) params.append('data_inicio', this.filters.data_inicio);
      if (this.filters.data_fim) params.append('data_fim', this.filters.data_fim);

      const response = await fetch(`/api/vendas?${params.toString()}`);
      const data = await response.json();
      this.vendas = data;
    },

    async fetchDashboard() {
      const response = await fetch('/api/relatorio');
      const data = await response.json();
      this.dashboard = data;
      this.renderCharts(data);
    },

    async salvarVenda() {
      const payload = { ...this.form };

      if (!payload.produto || !payload.preco || !payload.data || !payload.status || !payload.origem) {
        alert('Preencha todos os campos antes de salvar.');
        return;
      }

      const config = {
        method: this.editId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      };

      const url = this.editId ? `/api/vendas/${this.editId}` : '/api/vendas';
      const response = await fetch(url, config);
      const result = await response.json();

      if (!response.ok) {
        alert(result.error || 'Erro ao salvar venda.');
        return;
      }

      this.resetForm();
      this.fetchVendas();
      this.fetchDashboard();
    },

    async excluirVenda(id) {
      const confirmed = window.confirm('Deseja realmente excluir esta venda?');
      if (!confirmed) return;

      const response = await fetch(`/api/vendas/${id}`, { method: 'DELETE' });
      const result = await response.json();

      if (!response.ok) {
        alert(result.error || 'Erro ao excluir venda.');
        return;
      }

      this.fetchVendas();
      this.fetchDashboard();
    },

    editarVenda(venda) {
      this.editId = venda.id;
      this.form = {
        produto: venda.produto,
        preco: venda.preco,
        data: venda.data,
        status: venda.status,
        origem: venda.origem,
      };
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    cancelEdit() {
      this.resetForm();
    },

    resetForm() {
      this.editId = null;
      this.form = {
        produto: '',
        preco: '',
        data: '',
        status: '',
        origem: '',
      };
    },

    clearFilters() {
      this.filters = {
        q: '',
        status: '',
        origem: '',
        data_inicio: '',
        data_fim: '',
      };
    },

    renderCharts(data) {
      const statusLabels = data.status?.map(item => item.status) || [];
      const statusValues = data.status?.map(item => Number(item.total)) || [];
      const origemLabels = data.origem?.map(item => item.origem) || [];
      const origemValues = data.origem?.map(item => Number(item.total)) || [];

      this.renderChart('statusChart', 'Status do pedido', statusLabels, statusValues, 'bar');
      this.renderChart('origemChart', 'Origem', origemLabels, origemValues, 'doughnut');
    },

    renderChart(canvasId, label, labels, values, type) {
      const canvas = document.getElementById(canvasId);
      if (!canvas) return;

      const instanceKey = `${canvasId}Instance`;
      if (this[instanceKey]) {
        this[instanceKey].destroy();
      }

      const chart = new Chart(canvas, {
        type,
        data: {
          labels,
          datasets: [{
            label,
            data: values,
            backgroundColor: type === 'doughnut'
              ? ['#2f6fed', '#1fa77a', '#f2a93b', '#e14b45', '#8b5cf6', '#0ea5e9']
              : '#2f6fed',
            borderRadius: 8,
            borderWidth: 1,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' },
          },
          scales: type === 'bar' ? {
            y: {
              beginAtZero: true,
              ticks: { precision: 0 },
            },
          } : undefined,
        },
      });

      this[instanceKey] = chart;
    },

    formatCurrency(value) {
      return Number(value || 0).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    },

    formatDate(value) {
      if (!value) return '-';
      const date = new Date(value + 'T00:00:00');
      return date.toLocaleDateString('pt-BR');
    },

    statusClass(status) {
      return String(status || '').toLowerCase();
    },

    async exportCsv() {
      const response = await fetch('/api/export/csv');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'vendas.csv';
      a.click();
      window.URL.revokeObjectURL(url);
    },
  },
}).mount('#app');
