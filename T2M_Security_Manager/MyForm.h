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
using namespace System::Text;

namespace T2MSecurityManager {

	public ref class MyForm : public System::Windows::Forms::Form
	{
	public:
		MyForm(void)
		{
			InitializeComponent();

			// --- BOTÃO GERAR IA ---
			this->btnGerarIA = (gcnew System::Windows::Forms::Button());
			this->btnGerarIA->Name = L"btnGerarIA";
			this->btnGerarIA->Text = L"✨ Gerar Script com IA";
			this->btnGerarIA->Location = System::Drawing::Point(20, 660);
			this->btnGerarIA->Size = System::Drawing::Size(200, 35);
			this->btnGerarIA->BackColor = System::Drawing::Color::Indigo;
			this->btnGerarIA->ForeColor = System::Drawing::Color::White;
			this->btnGerarIA->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnGerarIA->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9, System::Drawing::FontStyle::Bold));
			this->btnGerarIA->Click += gcnew System::EventHandler(this, &MyForm::btnGerarIA_Click);
			this->Controls->Add(this->btnGerarIA);

			scriptPaths = gcnew Dictionary<String^, String^>();

			try {
				if (File::Exists("T2M_logo-03.png")) {
					this->picLogo->Image = System::Drawing::Image::FromFile("T2M_logo-03.png");
				}
			}
			catch (...) {}

			try {
				if (File::Exists("T2M_logo-03.png")) {
					System::Drawing::Bitmap^ bmp = gcnew System::Drawing::Bitmap("T2M_logo-03.png");
					this->Icon = System::Drawing::Icon::FromHandle(bmp->GetHicon());
				}
			}
			catch (...) {}

			CarregarConfiguracao();
			CarregarScriptsIA();
		}

	protected:
		~MyForm()
		{
			if (components) delete components;
		}

	private:
		Dictionary<String^, String^>^ scriptPaths;
		Process^ pythonProcess;

		System::Windows::Forms::PictureBox^ picLogo;
		System::Windows::Forms::ListBox^ lstScripts;
		System::Windows::Forms::Button^ btnAdd;
		System::Windows::Forms::Button^ btnRemove;
		System::Windows::Forms::Button^ btnAbrirPasta;
		System::Windows::Forms::RichTextBox^ txtOutput;
		System::Windows::Forms::Label^ lblUrl;
		System::Windows::Forms::TextBox^ txtUrl;
		System::Windows::Forms::Label^ lblToken;
		System::Windows::Forms::TextBox^ txtToken;
		System::Windows::Forms::Button^ btnLoginAuto;
		System::Windows::Forms::CheckBox^ chkHabilitarLogin;
		System::Windows::Forms::Button^ btnGerarIA;
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
			this->btnAbrirPasta = (gcnew System::Windows::Forms::Button());
			this->txtOutput = (gcnew System::Windows::Forms::RichTextBox());
			this->lblUrl = (gcnew System::Windows::Forms::Label());
			this->txtUrl = (gcnew System::Windows::Forms::TextBox());
			this->lblToken = (gcnew System::Windows::Forms::Label());
			this->txtToken = (gcnew System::Windows::Forms::TextBox());
			this->btnLoginAuto = (gcnew System::Windows::Forms::Button());
			this->chkHabilitarLogin = (gcnew System::Windows::Forms::CheckBox());
			this->chkSalvar = (gcnew System::Windows::Forms::CheckBox());
			this->btnStart = (gcnew System::Windows::Forms::Button());
			this->btnStop = (gcnew System::Windows::Forms::Button());
			this->btnExport = (gcnew System::Windows::Forms::Button());
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->picLogo))->BeginInit();
			this->SuspendLayout();

			this->picLogo->BackColor = System::Drawing::Color::Transparent;
			this->picLogo->Location = System::Drawing::Point(20, 15);
			this->picLogo->Name = L"picLogo";
			this->picLogo->Size = System::Drawing::Size(200, 60);
			this->picLogo->SizeMode = System::Windows::Forms::PictureBoxSizeMode::Zoom;
			this->picLogo->TabIndex = 0;
			this->picLogo->TabStop = false;

			this->lstScripts->Font = (gcnew System::Drawing::Font(L"Segoe UI", 10));
			this->lstScripts->ItemHeight = 17;
			this->lstScripts->Location = System::Drawing::Point(20, 140);
			this->lstScripts->Name = L"lstScripts";
			this->lstScripts->Size = System::Drawing::Size(200, 514);
			this->lstScripts->TabIndex = 1;

			this->btnAdd->BackColor = System::Drawing::Color::LightGreen;
			this->btnAdd->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnAdd->Location = System::Drawing::Point(20, 90);
			this->btnAdd->Name = L"btnAdd";
			this->btnAdd->Size = System::Drawing::Size(80, 35);
			this->btnAdd->TabIndex = 2;
			this->btnAdd->Text = L"+ Add";
			this->btnAdd->UseVisualStyleBackColor = false;
			this->btnAdd->Click += gcnew System::EventHandler(this, &MyForm::btnAdd_Click);

			this->btnRemove->BackColor = System::Drawing::Color::LightCoral;
			this->btnRemove->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnRemove->Location = System::Drawing::Point(105, 90);
			this->btnRemove->Name = L"btnRemove";
			this->btnRemove->Size = System::Drawing::Size(75, 35);
			this->btnRemove->TabIndex = 3;
			this->btnRemove->Text = L"Remover";
			this->btnRemove->UseVisualStyleBackColor = false;
			this->btnRemove->Click += gcnew System::EventHandler(this, &MyForm::btnRemove_Click);

			this->btnAbrirPasta->BackColor = System::Drawing::Color::LightSkyBlue;
			this->btnAbrirPasta->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnAbrirPasta->Location = System::Drawing::Point(185, 90);
			this->btnAbrirPasta->Name = L"btnAbrirPasta";
			this->btnAbrirPasta->Size = System::Drawing::Size(35, 35);
			this->btnAbrirPasta->TabIndex = 4;
			this->btnAbrirPasta->Text = L"📂";
			this->btnAbrirPasta->UseVisualStyleBackColor = false;
			this->btnAbrirPasta->Click += gcnew System::EventHandler(this, &MyForm::btnAbrirPasta_Click);

			this->txtOutput->BackColor = System::Drawing::Color::FromArgb(static_cast<System::Int32>(static_cast<System::Byte>(30)), static_cast<System::Int32>(static_cast<System::Byte>(30)),
				static_cast<System::Int32>(static_cast<System::Byte>(30)));
			this->txtOutput->Font = (gcnew System::Drawing::Font(L"Consolas", 10));
			this->txtOutput->ForeColor = System::Drawing::Color::LimeGreen;
			this->txtOutput->Location = System::Drawing::Point(240, 90);
			this->txtOutput->Name = L"txtOutput";
			this->txtOutput->ReadOnly = true;
			this->txtOutput->Size = System::Drawing::Size(660, 360);
			this->txtOutput->TabIndex = 5;
			this->txtOutput->Text = L"";

			this->lblUrl->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9, System::Drawing::FontStyle::Bold));
			this->lblUrl->ForeColor = System::Drawing::Color::DarkRed;
			this->lblUrl->Location = System::Drawing::Point(240, 460);
			this->lblUrl->Name = L"lblUrl";
			this->lblUrl->Size = System::Drawing::Size(100, 20);
			this->lblUrl->TabIndex = 6;
			this->lblUrl->Text = L"URL Alvo:";

			this->txtUrl->Font = (gcnew System::Drawing::Font(L"Segoe UI", 10));
			this->txtUrl->Location = System::Drawing::Point(240, 480);
			this->txtUrl->Name = L"txtUrl";
			this->txtUrl->Size = System::Drawing::Size(660, 25);
			this->txtUrl->TabIndex = 7;

			this->lblToken->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9, System::Drawing::FontStyle::Bold));
			this->lblToken->ForeColor = System::Drawing::Color::DarkBlue;
			this->lblToken->Location = System::Drawing::Point(240, 515);
			this->lblToken->Name = L"lblToken";
			this->lblToken->Size = System::Drawing::Size(100, 20);
			this->lblToken->TabIndex = 8;
			this->lblToken->Text = L"Token JWT:";

			this->txtToken->Font = (gcnew System::Drawing::Font(L"Segoe UI", 10));
			this->txtToken->Location = System::Drawing::Point(240, 535);
			this->txtToken->Name = L"txtToken";
			this->txtToken->Size = System::Drawing::Size(660, 25);
			this->txtToken->TabIndex = 11;

			this->btnLoginAuto->BackColor = System::Drawing::Color::Silver;
			this->btnLoginAuto->Enabled = false;
			this->btnLoginAuto->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnLoginAuto->Font = (gcnew System::Drawing::Font(L"Segoe UI", 8, System::Drawing::FontStyle::Bold));
			this->btnLoginAuto->Location = System::Drawing::Point(740, 510);
			this->btnLoginAuto->Name = L"btnLoginAuto";
			this->btnLoginAuto->Size = System::Drawing::Size(160, 25);
			this->btnLoginAuto->TabIndex = 10;
			this->btnLoginAuto->Text = L"🔑 Login Automático";
			this->btnLoginAuto->UseVisualStyleBackColor = false;
			this->btnLoginAuto->Click += gcnew System::EventHandler(this, &MyForm::btnLoginAuto_Click);

			this->chkHabilitarLogin->Font = (gcnew System::Drawing::Font(L"Segoe UI", 8));
			this->chkHabilitarLogin->Location = System::Drawing::Point(660, 513);
			this->chkHabilitarLogin->Name = L"chkHabilitarLogin";
			this->chkHabilitarLogin->Size = System::Drawing::Size(80, 20);
			this->chkHabilitarLogin->TabIndex = 9;
			this->chkHabilitarLogin->Text = L"Ativar";
			this->chkHabilitarLogin->CheckedChanged += gcnew System::EventHandler(this, &MyForm::chkHabilitarLogin_CheckedChanged);

			this->chkSalvar->Checked = true;
			this->chkSalvar->CheckState = System::Windows::Forms::CheckState::Checked;
			this->chkSalvar->Font = (gcnew System::Drawing::Font(L"Segoe UI", 9));
			this->chkSalvar->Location = System::Drawing::Point(240, 570);
			this->chkSalvar->Name = L"chkSalvar";
			this->chkSalvar->Size = System::Drawing::Size(300, 25);
			this->chkSalvar->TabIndex = 12;
			this->chkSalvar->Text = L"Salvar configurações ao sair";

			this->btnStart->BackColor = System::Drawing::Color::YellowGreen;
			this->btnStart->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnStart->Location = System::Drawing::Point(240, 600);
			this->btnStart->Name = L"btnStart";
			this->btnStart->Size = System::Drawing::Size(180, 45);
			this->btnStart->TabIndex = 13;
			this->btnStart->Text = L"▶ INICIAR TESTE";
			this->btnStart->UseVisualStyleBackColor = false;
			this->btnStart->Click += gcnew System::EventHandler(this, &MyForm::btnStart_Click);

			this->btnStop->BackColor = System::Drawing::Color::IndianRed;
			this->btnStop->Enabled = false;
			this->btnStop->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnStop->Location = System::Drawing::Point(480, 600);
			this->btnStop->Name = L"btnStop";
			this->btnStop->Size = System::Drawing::Size(180, 45);
			this->btnStop->TabIndex = 14;
			this->btnStop->Text = L"⏹ PARAR";
			this->btnStop->UseVisualStyleBackColor = false;
			this->btnStop->Click += gcnew System::EventHandler(this, &MyForm::btnStop_Click);

			this->btnExport->BackColor = System::Drawing::Color::LightGray;
			this->btnExport->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->btnExport->Location = System::Drawing::Point(720, 600);
			this->btnExport->Name = L"btnExport";
			this->btnExport->Size = System::Drawing::Size(180, 45);
			this->btnExport->TabIndex = 15;
			this->btnExport->Text = L"💾 Exportar Log";
			this->btnExport->UseVisualStyleBackColor = false;
			this->btnExport->Click += gcnew System::EventHandler(this, &MyForm::btnExport_Click);

			this->BackColor = System::Drawing::Color::WhiteSmoke;
			this->ClientSize = System::Drawing::Size(924, 711);
			this->Controls->Add(this->picLogo);
			this->Controls->Add(this->lstScripts);
			this->Controls->Add(this->btnAdd);
			this->Controls->Add(this->btnRemove);
			this->Controls->Add(this->btnAbrirPasta);
			this->Controls->Add(this->txtOutput);
			this->Controls->Add(this->lblUrl);
			this->Controls->Add(this->txtUrl);
			this->Controls->Add(this->lblToken);
			this->Controls->Add(this->chkHabilitarLogin);
			this->Controls->Add(this->btnLoginAuto);
			this->Controls->Add(this->txtToken);
			this->Controls->Add(this->chkSalvar);
			this->Controls->Add(this->btnStart);
			this->Controls->Add(this->btnStop);
			this->Controls->Add(this->btnExport);
			this->Name = L"MyForm";
			this->StartPosition = System::Windows::Forms::FormStartPosition::CenterScreen;
			this->Text = L"T2M Security Manager v4.0 (Safe Mode)"; // <-- ATUALIZADO PARA V4.0
			this->FormClosing += gcnew System::Windows::Forms::FormClosingEventHandler(this, &MyForm::MyForm_FormClosing);
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->picLogo))->EndInit();
			this->ResumeLayout(false);
			this->PerformLayout();
		}
#pragma endregion

	private: System::Void chkHabilitarLogin_CheckedChanged(System::Object^ sender, System::EventArgs^ e) {
		if (chkHabilitarLogin->Checked) {
			btnLoginAuto->Enabled = true;
			btnLoginAuto->BackColor = System::Drawing::Color::LightBlue;
		}
		else {
			btnLoginAuto->Enabled = false;
			btnLoginAuto->BackColor = System::Drawing::Color::Silver;
		}
	}

	private: System::Void btnLoginAuto_Click(System::Object^ sender, System::EventArgs^ e) {
		String^ urlAlvo = txtUrl->Text;
		if (String::IsNullOrWhiteSpace(urlAlvo)) {
			urlAlvo = "https://sgidd.t2mlab.com/auth";
			txtUrl->Text = urlAlvo;
		}

		txtUrl->Enabled = false;
		txtToken->Enabled = false;
		chkHabilitarLogin->Enabled = false;
		btnLoginAuto->Enabled = false;
		btnLoginAuto->BackColor = System::Drawing::Color::LightGray;
		btnLoginAuto->Text = L"⏳ Aguarde...";
		txtOutput->Clear();
		txtOutput->AppendText(">>> INICIANDO LOGIN AUTOMÁTICO...\n");

		ProcessStartInfo^ psi = gcnew ProcessStartInfo();
		psi->FileName = "python";
		psi->Arguments = "-u \"get_token.py\" \"" + urlAlvo + "\"";
		psi->UseShellExecute = false;
		psi->RedirectStandardOutput = true;
		psi->CreateNoWindow = true;
		psi->StandardOutputEncoding = System::Text::Encoding::UTF8;
		psi->EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

		Process^ pLogin = gcnew Process();
		pLogin->StartInfo = psi;

		try {
			pLogin->Start();
			String^ output = pLogin->StandardOutput->ReadToEnd();
			pLogin->WaitForExit();

			if (output->Contains("TOKEN_ENCONTRADO_INICIO")) {
				array<String^>^ partes = output->Split(gcnew array<String^>{"TOKEN_ENCONTRADO_INICIO", "TOKEN_ENCONTRADO_FIM"}, StringSplitOptions::None);
				if (partes->Length >= 2) {
					txtToken->Text = partes[1]->Trim();
					txtOutput->AppendText("\n>>> SUCESSO! Token capturado.\n");
					MessageBox::Show("Token capturado com sucesso!", "Login Auto");
				}
			}
			else {
				txtOutput->AppendText("\n>>> AVISO: Token não encontrado ou tempo esgotado.\n");
			}
		}
		catch (Exception^ ex) {
			MessageBox::Show("Erro: " + ex->Message);
		}

		txtUrl->Enabled = true;
		txtToken->Enabled = true;
		chkHabilitarLogin->Enabled = true;
		btnLoginAuto->Enabled = true;
		btnLoginAuto->BackColor = System::Drawing::Color::LightBlue;
		btnLoginAuto->Text = L"🔑 Login Automático";
	}

	private: void SalvarConfiguracao() {
		if (!chkSalvar->Checked) {
			if (File::Exists("config.txt")) File::Delete("config.txt");
			return;
		}
		try {
			StreamWriter^ sw = gcnew StreamWriter("config.txt");
			sw->WriteLine(txtUrl->Text);
			sw->WriteLine(txtToken->Text);
			for each (KeyValuePair<String^, String^> pair in scriptPaths) {
				sw->WriteLine(pair.Value);
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
			if (linha != nullptr) txtUrl->Text = linha;
			linha = sr->ReadLine();
			if (linha != nullptr) txtToken->Text = linha;
			while ((linha = sr->ReadLine()) != nullptr) {
				String^ caminho = linha;
				if (File::Exists(caminho)) {
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

	private: void CarregarScriptsIA() {
		try {
			String^ pastaDocumentos = Environment::GetFolderPath(Environment::SpecialFolder::MyDocuments);
			String^ pastaIA = Path::Combine(pastaDocumentos, "modelos de teste em IA");

			if (Directory::Exists(pastaIA)) {
				array<String^>^ arquivos = Directory::GetFiles(pastaIA, "*.py");
				for each (String ^ arquivo in arquivos) {
					String^ nome = Path::GetFileName(arquivo);
					if (!scriptPaths->ContainsKey(nome)) {
						scriptPaths->Add(nome, arquivo);
						lstScripts->Items->Add(nome);
					}
				}
			}
		}
		catch (...) {}
	}

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

	private: System::Void btnAbrirPasta_Click(System::Object^ sender, System::EventArgs^ e) {
		String^ pastaDocumentos = Environment::GetFolderPath(Environment::SpecialFolder::MyDocuments);
		String^ pastaIA = Path::Combine(pastaDocumentos, "modelos de teste em IA");

		if (Directory::Exists(pastaIA)) {
			Process::Start("explorer.exe", pastaIA);
		}
		else {
			MessageBox::Show("A pasta ainda não existe. Gere o seu primeiro script com a IA para a criar!", "Aviso", MessageBoxButtons::OK, MessageBoxIcon::Information);
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
		psi->StandardOutputEncoding = System::Text::Encoding::UTF8;
		psi->StandardErrorEncoding = System::Text::Encoding::UTF8;
		psi->EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

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

	private: void CarregarDropdownAPI(ComboBox^ combo) {
		combo->Items->Clear();

		List<String^>^ chavesValidas = gcnew List<String^>();
		if (File::Exists("api_keys_ia.txt")) {
			array<String^>^ linhas = File::ReadAllLines("api_keys_ia.txt");
			for each (String ^ linha in linhas) {
				if (!String::IsNullOrWhiteSpace(linha)) {
					chavesValidas->Add(linha->Trim());
				}
			}
		}

		if (chavesValidas->Count > 0) {
			for each (String ^ chave in chavesValidas) {
				String^ chaveMascarada = chave;
				if (chave->Length > 15) {
					chaveMascarada = chave->Substring(0, 6) + "****************" + chave->Substring(chave->Length - 4);
				}
				combo->Items->Add(chaveMascarada);
			}
		}
		else {
			combo->Items->Add(" Nenhuma chave configurada ");
		}

		combo->Items->Add("-------------------------");
		combo->Items->Add("➕ Adicionar Nova API Key...");

		String^ ultimoUsado = "0";
		if (File::Exists("last_ai_key.txt")) {
			ultimoUsado = File::ReadAllText("last_ai_key.txt")->Trim();
		}

		int idx = 0;
		Int32::TryParse(ultimoUsado, idx);

		if (idx >= 0 && idx < combo->Items->Count && !combo->Items[idx]->ToString()->StartsWith("-") && !combo->Items[idx]->ToString()->StartsWith("➕")) {
			combo->SelectedIndex = idx;
		}
		else {
			combo->SelectedIndex = 0;
		}
	}

	private: System::Void btnGerarIA_Click(System::Object^ sender, System::EventArgs^ e) {
		if (txtUrl->Text->Trim() == "") {
			MessageBox::Show("Por favor, preencha a URL Alvo primeiro. A IA precisa saber qual site vai testar!", "Contexto Necessário", MessageBoxButtons::OK, MessageBoxIcon::Information);
			return;
		}

		Form^ formIA = gcnew Form();
		// <-- ATUALIZADO PARA MULTI-MODEL
		formIA->Text = "Gerador de Scripts de Segurança - IA (Multi-Model)";
		formIA->Size = System::Drawing::Size(450, 300);
		formIA->StartPosition = FormStartPosition::CenterParent;
		formIA->FormBorderStyle = System::Windows::Forms::FormBorderStyle::FixedDialog;
		formIA->MaximizeBox = false;

		ComboBox^ comboModelo = gcnew ComboBox();
		comboModelo->Name = "comboModelo";
		comboModelo->Location = System::Drawing::Point(20, 20);
		comboModelo->Size = System::Drawing::Size(350, 25);
		comboModelo->DropDownStyle = ComboBoxStyle::DropDownList;
		comboModelo->Font = gcnew System::Drawing::Font("Arial", 10, System::Drawing::FontStyle::Bold);
		CarregarDropdownAPI(comboModelo);
		formIA->Controls->Add(comboModelo);

		Button^ btnLixeira = gcnew Button();
		btnLixeira->Name = "btnLixeira";
		btnLixeira->Text = "X";
		btnLixeira->Font = gcnew System::Drawing::Font("Arial", 9, System::Drawing::FontStyle::Bold);
		btnLixeira->Location = System::Drawing::Point(380, 19);
		btnLixeira->Size = System::Drawing::Size(30, 27);
		btnLixeira->BackColor = System::Drawing::Color::IndianRed;
		btnLixeira->ForeColor = System::Drawing::Color::White;
		btnLixeira->FlatStyle = FlatStyle::Flat;
		btnLixeira->Enabled = (!comboModelo->Items[comboModelo->SelectedIndex]->ToString()->StartsWith(" Nenhuma"));
		btnLixeira->Click += gcnew System::EventHandler(this, &MyForm::btnLixeira_Click);
		formIA->Controls->Add(btnLixeira);

		ToolTip^ dicaLixeira = gcnew ToolTip();
		dicaLixeira->SetToolTip(btnLixeira, "Excluir a API Key selecionada");

		TextBox^ txtPrompt = gcnew TextBox();
		txtPrompt->Name = "txtPrompt";
		txtPrompt->Location = System::Drawing::Point(20, 60);
		txtPrompt->Size = System::Drawing::Size(390, 130);
		txtPrompt->Multiline = true;
		txtPrompt->Font = gcnew System::Drawing::Font("Arial", 10);
		txtPrompt->Text = "Descreva o teste que deseja fazer em poucas palavras...";
		txtPrompt->ForeColor = System::Drawing::Color::Gray;
		txtPrompt->GotFocus += gcnew System::EventHandler(this, &MyForm::Prompt_GotFocus);
		txtPrompt->LostFocus += gcnew System::EventHandler(this, &MyForm::Prompt_LostFocus);
		formIA->Controls->Add(txtPrompt);

		Button^ btnGerar = gcnew Button();
		btnGerar->Text = "Gerar Script";
		btnGerar->Location = System::Drawing::Point(20, 210);
		btnGerar->Size = System::Drawing::Size(190, 35);
		btnGerar->BackColor = System::Drawing::Color::MediumSeaGreen;
		btnGerar->ForeColor = System::Drawing::Color::White;
		btnGerar->FlatStyle = FlatStyle::Flat;
		btnGerar->Click += gcnew System::EventHandler(this, &MyForm::btnExecutarGeracaoIA_Click);
		formIA->Controls->Add(btnGerar);

		Button^ btnCancelar = gcnew Button();
		btnCancelar->Text = "Cancelar";
		btnCancelar->Location = System::Drawing::Point(220, 210);
		btnCancelar->Size = System::Drawing::Size(190, 35);
		btnCancelar->BackColor = System::Drawing::Color::IndianRed;
		btnCancelar->ForeColor = System::Drawing::Color::White;
		btnCancelar->FlatStyle = FlatStyle::Flat;
		btnCancelar->DialogResult = System::Windows::Forms::DialogResult::Cancel;
		formIA->Controls->Add(btnCancelar);

		comboModelo->SelectedIndexChanged += gcnew System::EventHandler(this, &MyForm::ComboModelo_Changed);

		formIA->ShowDialog();
	}

	private: System::Void ComboModelo_Changed(System::Object^ sender, System::EventArgs^ e) {
		ComboBox^ combo = (ComboBox^)sender;
		Form^ parentForm = combo->FindForm();
		Button^ btnLixeira = nullptr;

		if (parentForm != nullptr) {
			array<Control^>^ controls = parentForm->Controls->Find("btnLixeira", true);
			if (controls->Length > 0) btnLixeira = (Button^)controls[0];
		}

		if (combo->SelectedItem != nullptr && combo->SelectedItem->ToString()->StartsWith("---")) {
			combo->SelectedIndex = 0;
			return;
		}

		if (!combo->SelectedItem->ToString()->StartsWith(" Nenhuma") && !combo->SelectedItem->ToString()->StartsWith("➕")) {
			File::WriteAllText("last_ai_key.txt", combo->SelectedIndex.ToString());
		}

		if (btnLixeira != nullptr) {
			if (combo->SelectedIndex >= 0 && !combo->SelectedItem->ToString()->StartsWith("-") && !combo->SelectedItem->ToString()->StartsWith("➕") && !combo->SelectedItem->ToString()->StartsWith(" Nenhuma")) {
				btnLixeira->Enabled = true;
				btnLixeira->BackColor = System::Drawing::Color::IndianRed;
			}
			else {
				btnLixeira->Enabled = false;
				btnLixeira->BackColor = System::Drawing::Color::Gray;
			}
		}

		if (combo->SelectedItem != nullptr && combo->SelectedItem->ToString()->StartsWith("➕")) {
			Form^ formApi = gcnew Form();
			// <-- ATUALIZADO TÍTULO PARA EXPLICAR OPÇÕES
			formApi->Text = "Nova API Key (Gemini ou OpenAI)";
			formApi->Size = System::Drawing::Size(350, 150);
			formApi->StartPosition = FormStartPosition::CenterParent;
			formApi->FormBorderStyle = System::Windows::Forms::FormBorderStyle::FixedToolWindow;

			TextBox^ txtApi = gcnew TextBox();
			txtApi->Name = "txtApi";
			txtApi->Location = System::Drawing::Point(20, 20);
			txtApi->Size = System::Drawing::Size(290, 25);
			txtApi->PasswordChar = '*';
			formApi->Controls->Add(txtApi);

			Button^ btnSalvarApi = gcnew Button();
			btnSalvarApi->Text = "Salvar API";
			btnSalvarApi->Location = System::Drawing::Point(20, 60);
			btnSalvarApi->BackColor = System::Drawing::Color::MediumSeaGreen;
			btnSalvarApi->ForeColor = System::Drawing::Color::White;
			btnSalvarApi->FlatStyle = FlatStyle::Flat;

			btnSalvarApi->Tag = combo;
			btnSalvarApi->Click += gcnew System::EventHandler(this, &MyForm::btnSalvarApi_Click);
			formApi->Controls->Add(btnSalvarApi);

			Button^ btnCancApi = gcnew Button();
			btnCancApi->Text = "Cancelar";
			btnCancApi->Location = System::Drawing::Point(180, 60);
			btnCancApi->BackColor = System::Drawing::Color::IndianRed;
			btnCancApi->ForeColor = System::Drawing::Color::White;
			btnCancApi->FlatStyle = FlatStyle::Flat;
			btnCancApi->DialogResult = System::Windows::Forms::DialogResult::Cancel;
			formApi->Controls->Add(btnCancApi);

			formApi->ShowDialog();

			if (combo->SelectedItem->ToString()->StartsWith("➕")) {
				combo->SelectedIndex = 0;
			}
		}
	}

	private: System::Void btnLixeira_Click(System::Object^ sender, System::EventArgs^ e) {
		Button^ btnLixeira = (Button^)sender;
		Form^ parentForm = btnLixeira->FindForm();
		ComboBox^ combo = (ComboBox^)parentForm->Controls->Find("comboModelo", true)[0];

		if (MessageBox::Show("Deseja realmente excluir esta API Key do seu computador?", "Excluir Cofre", MessageBoxButtons::YesNo, MessageBoxIcon::Warning) == System::Windows::Forms::DialogResult::Yes) {
			int idxParaRemover = combo->SelectedIndex;

			if (File::Exists("api_keys_ia.txt")) {
				array<String^>^ linhas = File::ReadAllLines("api_keys_ia.txt");
				List<String^>^ chavesRestantes = gcnew List<String^>();
				int indexAtual = 0;
				for each (String ^ linha in linhas) {
					if (!String::IsNullOrWhiteSpace(linha)) {
						if (indexAtual != idxParaRemover) {
							chavesRestantes->Add(linha->Trim());
						}
						indexAtual++;
					}
				}
				File::WriteAllLines("api_keys_ia.txt", chavesRestantes->ToArray());
				CarregarDropdownAPI(combo);
			}
		}
	}

	private: System::Void btnSalvarApi_Click(System::Object^ sender, System::EventArgs^ e) {
		Button^ btn = (Button^)sender;
		TextBox^ txtApi = (TextBox^)btn->FindForm()->Controls->Find("txtApi", true)[0];
		ComboBox^ combo = (ComboBox^)btn->Tag;

		if (txtApi->Text->Length > 0) {
			StreamWriter^ sw = File::AppendText("api_keys_ia.txt");
			sw->WriteLine(txtApi->Text->Trim());
			sw->Close();

			MessageBox::Show("API Key adicionada ao Cofre com sucesso!", "Sucesso");
			btn->FindForm()->Close();

			CarregarDropdownAPI(combo);
			combo->SelectedIndex = combo->Items->Count - 3;
		}
	}

	private: System::Void Prompt_GotFocus(System::Object^ sender, System::EventArgs^ e) {
		TextBox^ txt = safe_cast<TextBox^>(sender);
		if (txt->Text == "Descreva o teste que deseja fazer em poucas palavras...") {
			txt->Text = "";
			txt->ForeColor = System::Drawing::Color::Black;
		}
	}

	private: System::Void Prompt_LostFocus(System::Object^ sender, System::EventArgs^ e) {
		TextBox^ txt = safe_cast<TextBox^>(sender);
		if (String::IsNullOrWhiteSpace(txt->Text)) {
			txt->Text = "Descreva o teste que deseja fazer em poucas palavras...";
			txt->ForeColor = System::Drawing::Color::Gray;
		}
	}

	private: System::Void btnExecutarGeracaoIA_Click(System::Object^ sender, System::EventArgs^ e) {
		Button^ btn = (Button^)sender;
		Form^ parentForm = btn->FindForm();
		TextBox^ txtPrompt = (TextBox^)parentForm->Controls->Find("txtPrompt", true)[0];
		ComboBox^ comboModelo = (ComboBox^)parentForm->Controls->Find("comboModelo", true)[0];

		String^ prompt = txtPrompt->Text;
		if (prompt == "Descreva o teste que deseja fazer em poucas palavras..." || prompt->Trim() == "") {
			MessageBox::Show("Por favor, digite um prompt válido.", "Aviso");
			return;
		}

		String^ apiKeyReal = "";
		int idx = comboModelo->SelectedIndex;
		if (File::Exists("api_keys_ia.txt") && !comboModelo->SelectedItem->ToString()->StartsWith(" Nenhuma")) {
			array<String^>^ linhas = File::ReadAllLines("api_keys_ia.txt");
			List<String^>^ chaves = gcnew List<String^>();
			for each (String ^ linha in linhas) {
				if (!String::IsNullOrWhiteSpace(linha)) chaves->Add(linha->Trim());
			}
			if (idx >= 0 && idx < chaves->Count) {
				apiKeyReal = chaves[idx];
			}
		}

		if (apiKeyReal == "" || apiKeyReal->Length < 10) {
			MessageBox::Show("Você precisa adicionar uma API Key válida do Gemini (AIza...) ou OpenAI (sk-...) no menu antes de gerar o script.\n\nEla ficará salva apenas no seu computador de forma segura.", "Cofre Vazio", MessageBoxButtons::OK, MessageBoxIcon::Warning);
			return;
		}

		String^ urlContexto = txtUrl->Text;

		btn->Text = "⏳ Pensando...";
		btn->Enabled = false;

		ProcessStartInfo^ psi = gcnew ProcessStartInfo();
		psi->FileName = "python";
		psi->Arguments = "-u \"gerador_ia.py\" \"" + apiKeyReal + "\" \"" + prompt + "\" \"" + urlContexto + "\"";
		psi->UseShellExecute = false;
		psi->RedirectStandardOutput = true;
		psi->CreateNoWindow = true;
		psi->StandardOutputEncoding = System::Text::Encoding::UTF8;

		Process^ pIA = gcnew Process();
		pIA->StartInfo = psi;

		try {
			pIA->Start();
			String^ output = pIA->StandardOutput->ReadToEnd();
			pIA->WaitForExit();

			if (output->Contains("SUCESSO_IA:")) {
				array<String^>^ partes = output->Split(gcnew array<String^>{"SUCESSO_IA:"}, StringSplitOptions::None);
				if (partes->Length > 1) {
					String^ caminhoCompleto = partes[1]->Trim();
					String^ nomeArquivo = Path::GetFileName(caminhoCompleto);

					MessageBox::Show("Sucesso! Novo script criado e salvo em Documentos:\n" + nomeArquivo, "IA Concluída");

					if (!scriptPaths->ContainsKey(nomeArquivo)) {
						scriptPaths->Add(nomeArquivo, caminhoCompleto);
						lstScripts->Items->Add(nomeArquivo);
					}
				}
				parentForm->Close();
			}
			else {
				MessageBox::Show("Erro ao gerar:\n" + output, "Aviso/Erro");
				btn->Text = "Gerar Script";
				btn->Enabled = true;
			}
		}
		catch (Exception^ ex) {
			MessageBox::Show("Erro ao conectar com o script Python: " + ex->Message);
			btn->Text = "Gerar Script";
			btn->Enabled = true;
		}
	}

	};
}