#include <limits>
#include <vector>
#include <algorithm>

using namespace std;

float ED(const std::vector<unsigned long long> hyp, const std::vector<unsigned long long> ref, const int norm){
      
    std::vector<float> row(hyp.size() + 1, 1); 
    for(float i = 0; i < row.size(); ++i){
        row[i] = i;
    }
    std::vector<float> nextRow(hyp.size() + 1, std::numeric_limits<float>::max());

    
    for(int w = 1; w < ref.size() + 1; ++w){      
        for(int i = 0; i < hyp.size() + 1; ++i){ 
            if(i > 0){      
              nextRow[i] = std::min({nextRow[i-1] + 1, row[i-1] + (ref[w-1] != hyp[i-1]), row[i]+ 1});        
            }
            else{
              nextRow[i] = row[i]+ 1.0;
            }
        }  
        row = nextRow;
        nextRow.assign(nextRow.size() ,std::numeric_limits<float>::max());
    }  
    
    float errors = row[row.size()-1];
    return (errors)/(norm);     
}

//C wrapper for the C++ implementation. Communication channel with Python.
extern "C" float wrapper(const unsigned long long* hyp, const unsigned long long* ref, const int len_h, const int len_r, const int norm){
  std::vector<unsigned long long> hyp_vec(hyp,hyp+len_h);
  std::vector<unsigned long long> ref_vec(ref,ref+len_r);
  
  return ED(hyp_vec, ref_vec, norm);
}