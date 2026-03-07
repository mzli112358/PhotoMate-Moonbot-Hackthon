#include <chrono>
#include <iomanip>
#include <iostream>
#include <fstream>
#include <limits>
#include <sstream>
#include <string>
#include <unordered_set>
#include <vector>
#include <thread>

#include "galbot_robot.hpp"

// 添加的命令帮助表结构
struct CommandInfo {
  std::string cmd;
  std::string description;
  std::string parameters;
  std::string example;
};

// 命令帮助表
const std::vector<CommandInfo> COMMAND_TABLE = {
    {"start_microphone_stream_input", "启动麦克风流式音频输入功能", "无参数", "start_microphone_stream_input"},
    {"stop_microphone_stream_input", "停止指定的麦克风流式音频输入", "无参数", "stop_microphone_stream_input"},
    {"write_audio_stream_output", "将PCM格式的音频数据块写入音频输出流进行实时播放", "播放的音频文件名 (16K 16bit Mono PCM格式的音频文件路径)", "write_audio_stream_output"},
    {"stop_audio_stream_output", "停止指定的音频输出流或所有活跃的音频输出流播放", "无参数", "stop_audio_stream_output"},
    {"set_volume", "设置系统全局音量值", "音量设置参数 (0-100)", "set_volume"},
    {"get_volume", "获取当前系统全局音量值", "无参数", "get_volume"},
    {"help", "显示帮助", "无参数", "help"},
    {"q", "退出程序", "无参数", "q"}};

// 打印命令帮助表
void printCommandHelp() {
  std::cout << "\n================ 命令帮助表 =================" << std::endl;
  std::cout << std::left << std::setw(30) << "命令" << std::setw(30) << "描述" << std::setw(30) << "参数"
            << std::setw(30) << "示例" << std::endl;
  std::cout << std::string(110, '-') << std::endl;

  for (const auto& cmd : COMMAND_TABLE) {
    std::cout << std::left << std::setw(40) << cmd.cmd << std::setw(60) << cmd.description << std::setw(40)
              << cmd.parameters << std::setw(30) << cmd.example << std::endl;
  }
  std::cout << "=============================================\n" << std::endl;
}


void save_audio_data(const std::shared_ptr<galbot::sdk::g1::AudioData>& audio_data) {
  if (audio_data == nullptr) {
    std::cout << "audio_data is nullptr" << std::endl;
    return;
  }

  // std::cout << "Mic audio timestamp_ns: " << audio_data->header.timestamp_ns << std::endl;
  // std::cout << "frame_id is " << audio_data->header.frame_id << std::endl;
  // std::cout << "type is " << audio_data->type << std::endl;
  // std::cout << "format is " << audio_data->format << std::endl;
  // std::cout << "data size is " << audio_data->data.size() << std::endl;

  if (audio_data->type == "denoise_chunk" && audio_data->format == "pcm" && audio_data->data.size() > 0)
  {
    // std::cout << "save audio data:" << std::endl;
    std::ofstream outfile("denoise_audio.pcm", std::ios::app);
    outfile.write(reinterpret_cast<char *>(audio_data->data.data()), audio_data->data.size());
    // std::cout << "音频已保存至 result_audio.pcm" << std::endl;
  }
}


// 安全读取多种类型的数值输入，处理输入错误
template<typename T>
bool safe_read_number(T& value, const std::string& prompt = "") {
  if (!prompt.empty()) {
    std::cout << prompt;
  }

  std::string input;
  std::getline(std::cin, input);

  // 检查输入流状态
  if (std::cin.fail() && !std::cin.eof()) {
    std::cin.clear();
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    std::cout << "输入错误，请输入有效的数值。" << std::endl;
    return false;
  }

  // 去除前后空格
  input.erase(0, input.find_first_not_of(" \t"));
  input.erase(input.find_last_not_of(" \t") + 1);

  if (input.empty()) {
    std::cout << "输入错误，请输入有效的数值。" << std::endl;
    return false;
  }

  try {
    size_t pos;
    T result;

    if (std::is_integral<T>()) {
      result = static_cast<T>(std::stoll(input, &pos));
    } else if (std::is_floating_point<T>()) {
      result = static_cast<T>(std::stold(input, &pos));
    }

    // 检查是否整个字符串都被转换了
    if (pos != input.length()) {
      std::cout << "输入错误，请输入有效的数值。" << std::endl;
      return false;
    }

    value = result;
    return true;
  } catch (const std::exception&) {
    std::cout << "输入错误，请输入有效的数值。" << std::endl;
    return false;
  }
}


// 安全读取文件名输入，处理输入错误
bool safe_read_file_name(std::string& file_name, const std::string& prompt = "") {
  if (!prompt.empty()) {
    std::cout << prompt;
  }

  std::getline(std::cin, file_name);

  // 检查输入流状态
  if (std::cin.fail() && !std::cin.eof()) {
    std::cin.clear();
    std::cin.ignore();
  }
  return true;
}

int main(int argc, char* argv[]) {
  std::cout << "start" << std::endl;
  // 获取base_instance实例
  auto& base_instance = galbot::sdk::g1::GalbotRobot::get_instance();

  if (!base_instance.init()) {
    std::cout << "base_instance init fail" << std::endl;
    return -1;
  }

  printCommandHelp();

  std::string cmd, stream_id;
  while (base_instance.is_running()) {
    std::cout << "输入测试的接口名：";
    std::string input_line;
    std::getline(std::cin, input_line);

    // 提取第一个单词作为命令（忽略后续参数）
    std::istringstream iss(input_line);
    iss >> cmd;

    // 如果输入为空，继续循环
    if (cmd.empty()) {
      continue;
    }
    if (cmd == "help") {
      printCommandHelp();
      continue;
    } else if (cmd == "start_microphone_stream_input") {
      stream_id = base_instance.start_microphone_stream_input([](const std::shared_ptr<galbot::sdk::g1::AudioData> audio_data){
        save_audio_data(audio_data);
      });

      std::cout << "Start microphone stream input, stream_id: "<< stream_id << std::endl;
    } else if (cmd == "stop_microphone_stream_input") {
      base_instance.stop_microphone_stream_input(stream_id);
      std::cout << "Stop microphone stream input, stream_id : " << stream_id << std::endl;
    } else if (cmd == "write_audio_stream_output") {
      std::string play_file;
      safe_read_file_name(play_file, "请输入要播放的音频文件名 (16K 16bit Mono PCM格式的音频文件路径): ");

      const auto chunk_size = 2560; // 2560字节的数据块大小
      std::vector<char> audio_chunk(chunk_size, 0);
      std::cout << "Write audio stream data..." << std::endl;
      std::ifstream infile(play_file, std::ios::binary);
      if (!infile) {
        std::cout << "Failed to open for reading: " << play_file << std::endl;
        continue;
      } else {
        stream_id = "spk_stream_output_test";
        while (infile) {
          infile.read(audio_chunk.data(), static_cast<std::streamsize>(chunk_size));
          std::streamsize bytes_read = infile.gcount();
          if (bytes_read <= 0) break;
          std::string out_chunk(audio_chunk.data(), bytes_read);
          base_instance.write_audio_stream_output(out_chunk, stream_id);
          std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
      }
      std::cout << "Write audio stream output, stream id : " << stream_id << std::endl;
    } else if (cmd == "stop_audio_stream_output") {
      base_instance.stop_audio_stream_output(stream_id);
      std::cout << "Stop audio stream output, stream id: " << stream_id << std::endl;
    } else if (cmd == "set_volume") {
      float volume = 60;
      if (!safe_read_number(volume, "请输入音量设置参数 (0-100): ")) {
        continue;
      }

      if (!base_instance.set_volume(volume)) {
        std::cout << "Failed to set volume: " << volume << std::endl;
        continue;
      }
      std::cout << "Set current volume: " << volume << std::endl;
    } else if (cmd == "get_volume") {
      auto volume = base_instance.get_volume();
      std::cout << "Get current volume: " << volume << std::endl;
    } else if (cmd == "q") {
      break;
    } else {
      std::cout << "Invalid input" << std::endl;
    }
  }

  base_instance.request_shutdown();
  base_instance.wait_for_shutdown();
  base_instance.destroy();

  std::cout << "proccess end" << std::endl;
  return 0;
}
