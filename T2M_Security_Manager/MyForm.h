#pragma once
#include <iostream>
#include <string>

using namespace System;
using namespace System::ComponentModel;
using namespace System::Collections;
using namespace System::Windows::Forms;
using namespace System::Data;
using namespace System::Drawing;
using namespace System::Diagnostics;
using namespace System::IO;
using namespace System::Collections::Generic;

namespace T2MSecurityManager {

	public ref class MyForm : public System::Windows::Forms::Form
	{
	public:
		MyForm(void)
		{
			InitializeComponent();
			scriptPaths = gcnew Dictionary<String^, String^>();

			// 1. Tenta carregar o logo
			try {
				this->picLogo->Image = System::Drawing::Image::FromFile("T2M_logo-03.png");
			}
			catch (...) {}

			// 2. Carrega configurações salvas (se existirem)
			CarregarConfiguracao();
		}

	protected:
		~MyForm()
		{
			if (components) delete components;
		}

	private:
		// Variáveis
		Dictionary<String^, String^>^ scriptPaths;
		Process^ pythonProcess;

		// Componentes Visuais
		System::Windows::Forms::PictureBox^ picLogo;
		System::Windows::Forms::ListBox^ lstScripts;
		System::Windows::Forms::Button^ btnAdd;
		System::Windows::Forms::Button^ btnRemove;
		System::Windows::Forms::RichTextBox^ txtOutput;

		System::Windows::Forms::Label^ lblUrl;
		System::Windows::Forms::TextBox^ txtUrl;
		System::Windows::Forms::Label^ lblToken;
		System::Windows::Forms::TextBox^ txtToken;

		System::Windows::Forms::CheckBox^ chkSalvar;

		System::Windows::Forms::Button^ btnStart;
		System::Windows::Forms::Button^ btnStop;
		System::Windows::Forms::Button^ btnExport;
		System::ComponentModel::Container^ components;

#pragma region Windows Form Designer generated code
		void InitializeComponent(void)
		{
			this->picLogo = (gcnew System::Windows::Forms::PictureBox());
			this->lstScripts = (gcnew System::Windows::Forms::ListBox());
			this->btnAdd = (gcnew System::Windows::Forms::Button());
			this->btnRemove = (gcnew System::Windows::Forms::Button());
			this->txtOutput = (gcnew System::Windows::Forms::RichTextBox());

			this->lblUrl = (gcnew System::Windows::Forms::Label());
			this->txtUrl = (gcnew System::Windows::Forms::TextBox());

			this->lblToken = (gcnew System::Windows::Forms::Label());
			this->txtToken = (gcnew System::Windows::Forms::TextBox());

			this->chkSalvar = (gcnew System::Windows::Forms::CheckBox());

			this->btnStart = (gcnew System::Windows::Forms::Button());
			this->btnStop = (gcnew System::Windows::Forms::Button());
			this->btnExport = (gcnew System::Windows::Forms::Button());
			this->SuspendLayout();

			// Janela
			this->Text = L"T2M Security Manager v2.1";
			this->Size = System::Drawing::Size(940, 750);
			this->BackColor = System::Drawing::Color::WhiteSmoke;
			this->StartPosition = System::Windows::Forms::FormStartPosition::CenterScreen;
			this->FormClosing += gcnew System::Windows::Forms::FormClosingEventHandler(this, &MyForm::MyForm_FormClosing);

			// Logo
			this->picLogo->Location = System::Drawing::Point(20, 15);
			this->picLogo->Size = System::Drawing::Size(200, 60);
			this->picLogo->SizeMode = System::Windows::Forms::PictureBoxSizeMode::Zoom;
			this->picLogo->BackColor = System::Drawing::Color::Transparent;

			// Botões Esquerda
			this->btnAdd->Location = System::Drawing::Point(20, 90);
			this->btnAdd->Size = System::Drawing::Size(100, 35);
			this->btnAdd->Text = L"+ Adicionar";
			this->btnAdd->BackColor = System::Drawing::Color::LightGreen;
			this->btnAdd->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnAdd->Click += gcnew System::EventHandler(this, &MyForm::btnAdd_Click);

			this->btnRemove->Location = System::Drawing::Point(130, 90);
			this->btnRemove->Size = System::Drawing::Size(90, 35);
			this->btnRemove->Text = L"Remover";
			this->btnRemove->BackColor = System::Drawing::Color::LightCoral;
			this->btnRemove->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnRemove->Click += gcnew System::EventHandler(this, &MyForm::btnRemove_Click);

			// Lista Scripts
			this->lstScripts->Location = System::Drawing::Point(20, 140);
			this->lstScripts->Size = System::Drawing::Size(200, 520);
			this->lstScripts->Font = (gcnew System::Drawing::Font(L"Segoe UI", 10));

			// Relatório
			this->txtOutput->Location = System::Drawing::Point(240, 90);
			this->txtOutput->Size = System::Drawing::Size(660, 360);
			this->txtOutput->ReadOnly = true;
			this->txtOutput->BackColor = System::Drawing::Color::FromArgb(30, 30, 30);
			this->txtOutput->ForeColor = System::Drawing::Color::LimeGreen;
			this->txtOutput->Font = (gcnew System::Drawing::Font(L"Consolas", 10));

			// --- URL (AGORA VAZIO) ---
			this->lblUrl->Location = System::Drawing::Point(240, 460);
			this->lblUrl->Size = System::Drawing::Size(100, 20);
			this->lblUrl->Text = L"URL Alvo:";
			this->lblUrl->ForeColor = System::Drawing::Color::DarkRed;
			this->lblUrl->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9, System::Drawing::FontStyle::Bold));

			this->txtUrl->Location = System::Drawing::Point(240, 480);
			this->txtUrl->Size = System::Drawing::Size(660, 25);
			this->txtUrl->Font = (gcnew System::Drawing::Font(L"Segoe UI", 10));
			this->txtUrl->Text = L""; // <--- MUDANÇA AQUI: Começa vazio!

			// --- TOKEN ---
			this->lblToken->Location = System::Drawing::Point(240, 515);
			this->lblToken->Size = System::Drawing::Size(100, 20);
			this->lblToken->Text = L"Token JWT:";
			this->lblToken->ForeColor = System::Drawing::Color::DarkBlue;
			this->lblToken->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9, System::Drawing::FontStyle::Bold));

			this->txtToken->Location = System::Drawing::Point(240, 535);
			this->txtToken->Size = System::Drawing::Size(660, 25);
			this->txtToken->Font = (gcnew System::Drawing::Font(L"Segoe UI", 10));
			this->txtToken->Text = L"";

			// --- CHECKBOX SALVAR ---
			this->chkSalvar->Location = System::Drawing::Point(240, 570);
			this->chkSalvar->Size = System::Drawing::Size(300, 25);
			this->chkSalvar->Text = L"Salvar configurações ao sair (Scripts, URL e Token)";
			this->chkSalvar->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9));
			this->chkSalvar->Checked = true;

			// Botões
			this->btnStart->Location = System::Drawing::Point(240, 600);
			this->btnStart->Size = System::Drawing::Size(180, 45);
			this->btnStart->Text = L"▶ INICIAR TESTE";
			this->btnStart->BackColor = System::Drawing::Color::YellowGreen;
			this->btnStart->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnStart->Click += gcnew System::EventHandler(this, &MyForm::btnStart_Click);

			this->btnStop->Location = System::Drawing::Point(480, 600);
			this->btnStop->Size = System::Drawing::Size(180, 45);
			this->btnStop->Text = L"⏹ PARAR";
			this->btnStop->BackColor = System::Drawing::Color::IndianRed;
			this->btnStop->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnStop->Enabled = false;
			this->btnStop->Click += gcnew System::EventHandler(this, &MyForm::btnStop_Click);

			this->btnExport->Location = System::Drawing::Point(720, 600);
			this->btnExport->Size = System::Drawing::Size(180, 45);
			this->btnExport->Text = L"💾 Exportar Log";
			this->btnExport->BackColor = System::Drawing::Color::LightGray;
			this->btnExport->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnExport->Click += gcnew System::EventHandler(this, &MyForm::btnExport_Click);

			this->Controls->Add(this->picLogo);
			this->Controls->Add(this->lstScripts);
			this->Controls->Add(this->btnAdd);
			this->Controls->Add(this->btnRemove);
			this->Controls->Add(this->txtOutput);
			this->Controls->Add(this->lblUrl);
			this->Controls->Add(this->txtUrl);
			this->Controls->Add(this->lblToken);
			this->Controls->Add(this->txtToken);
			this->Controls->Add(this->chkSalvar);
			this->Controls->Add(this->btnStart);
			this->Controls->Add(this->btnStop);
			this->Controls->Add(this->btnExport);

			this->ResumeLayout(false);
			this->PerformLayout();
		}
#pragma endregion

		// =========================================================
		//   MÉTODOS DE SALVAR E CARREGAR
		// =========================================================

	private: void SalvarConfiguracao() {
		if (!chkSalvar->Checked) {
			if (File::Exists("config.txt")) File::Delete("config.txt");
			return;
		}

		try {
			StreamWriter^ sw = gcnew StreamWriter("config.txt");
			sw->WriteLine(txtUrl->Text);    // Linha 1: URL
			sw->WriteLine(txtToken->Text);  // Linha 2: Token
			for each (KeyValuePair<String^, String^> pair in scriptPaths) {
				sw->WriteLine(pair.Value);  // Linhas 3+: Scripts
			}
			sw->Close();
		}
		catch (...) {}
	}

	private: void CarregarConfiguracao() {
		if (!File::Exists("config.txt")) return;

		try {
			StreamReader^ sr = gcnew StreamReader("config.txt");

			String^ linha = sr->ReadLine();
			if (linha != nullptr) txtUrl->Text = linha; // Restaura URL se existir

			linha = sr->ReadLine();
			if (linha != nullptr) txtToken->Text = linha; // Restaura Token

			while ((linha = sr->ReadLine()) != nullptr) {
				String^ caminho = linha;
				if (File::Exists(caminho)) { // Só adiciona se o script ainda existir na pasta
					String^ nome = Path::GetFileName(caminho);
					if (!scriptPaths->ContainsKey(nome)) {
						scriptPaths->Add(nome, caminho);
						lstScripts->Items->Add(nome);
					}
				}
			}
			sr->Close();
			chkSalvar->Checked = true;
		}
		catch (...) {}
	}

		   // =========================================================
		   //   EVENTOS
		   // =========================================================

	private: System::Void MyForm_FormClosing(System::Object^ sender, System::Windows::Forms::FormClosingEventArgs^ e) {
		SalvarConfiguracao();
	}

	private: System::Void btnAdd_Click(System::Object^ sender, System::EventArgs^ e) {
		OpenFileDialog^ openFile = gcnew OpenFileDialog();
		openFile->Filter = "Python Scripts (*.py)|*.py";
		if (openFile->ShowDialog() == System::Windows::Forms::DialogResult::OK) {
			String^ caminho = openFile->FileName;
			String^ nome = Path::GetFileName(caminho);
			if (!scriptPaths->ContainsKey(nome)) {
				scriptPaths->Add(nome, caminho);
				lstScripts->Items->Add(nome);
			}
		}
	}

	private: System::Void btnRemove_Click(System::Object^ sender, System::EventArgs^ e) {
		if (lstScripts->SelectedIndex != -1) {
			scriptPaths->Remove(lstScripts->SelectedItem->ToString());
			lstScripts->Items->RemoveAt(lstScripts->SelectedIndex);
		}
	}

	private: System::Void btnStart_Click(System::Object^ sender, System::EventArgs^ e) {
		if (lstScripts->SelectedIndex == -1) {
			MessageBox::Show("Selecione um script!");
			return;
		}
		if (txtUrl->Text->Length == 0) {
			MessageBox::Show("Por favor, preencha o campo URL Alvo.");
			return;
		}

		String^ nome = lstScripts->SelectedItem->ToString();
		String^ caminho = scriptPaths[nome];
		String^ urlAlvo = txtUrl->Text;
		String^ tokenUsuario = txtToken->Text;

		txtOutput->Clear();
		txtOutput->AppendText(">>> INICIANDO TESTE DINÂMICO <<<\n");
		txtOutput->AppendText(">>> ALVO: " + urlAlvo + "\n");
		if (tokenUsuario->Length > 0) txtOutput->AppendText(">>> TOKEN: Carregado.\n");
		else txtOutput->AppendText(">>> TOKEN: Nenhum token informado.\n");
		txtOutput->AppendText("--------------------------------------------------\n");

		ProcessStartInfo^ psi = gcnew ProcessStartInfo();
		psi->FileName = "python";

		psi->Arguments = "-u \"" + caminho + "\" \"" + urlAlvo + "\" \"" + tokenUsuario + "\"";

		psi->UseShellExecute = false;
		psi->RedirectStandardOutput = true;
		psi->RedirectStandardError = true;
		psi->CreateNoWindow = true;

		pythonProcess = gcnew Process();
		pythonProcess->StartInfo = psi;

		pythonProcess->OutputDataReceived += gcnew DataReceivedEventHandler(this, &MyForm::OnDataReceived);
		pythonProcess->ErrorDataReceived += gcnew DataReceivedEventHandler(this, &MyForm::OnDataReceived);
		pythonProcess->EnableRaisingEvents = true;
		pythonProcess->Exited += gcnew EventHandler(this, &MyForm::OnProcessExited);

		try {
			pythonProcess->Start();
			pythonProcess->BeginOutputReadLine();
			pythonProcess->BeginErrorReadLine();
			btnStart->Enabled = false;
			btnStop->Enabled = true;
			txtUrl->Enabled = false;
			txtToken->Enabled = false;
		}
		catch (Exception^ ex) {
			MessageBox::Show("Erro Python: " + ex->Message);
		}
	}

	private: void OnDataReceived(System::Object^ sender, DataReceivedEventArgs^ e) {
		if (!String::IsNullOrEmpty(e->Data)) {
			this->Invoke(gcnew Action<String^>(this, &MyForm::AppendLog), e->Data);
		}
	}

	private: void AppendLog(String^ text) {
		txtOutput->AppendText(text + Environment::NewLine);
		txtOutput->ScrollToCaret();
	}

	private: void OnProcessExited(System::Object^ sender, EventArgs^ e) {
		this->Invoke(gcnew Action(this, &MyForm::ResetButtons));
	}

	private: void ResetButtons() {
		btnStart->Enabled = true;
		btnStop->Enabled = false;
		txtUrl->Enabled = true;
		txtToken->Enabled = true;
		txtOutput->AppendText("\n>>> FIM.");
	}

	private: System::Void btnStop_Click(System::Object^ sender, System::EventArgs^ e) {
		if (pythonProcess != nullptr && !pythonProcess->HasExited) {
			try { pythonProcess->Kill(); }
			catch (...) {}
		}
	}

	private: System::Void btnExport_Click(System::Object^ sender, System::EventArgs^ e) {
		SaveFileDialog^ save = gcnew SaveFileDialog();
		save->Filter = "Log (*.txt)|*.txt";
		if (save->ShowDialog() == System::Windows::Forms::DialogResult::OK) {
			File::WriteAllText(save->FileName, txtOutput->Text);
		}
	}
	};
}